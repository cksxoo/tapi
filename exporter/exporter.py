from prometheus_client import start_http_server, Gauge, Counter
import sqlite3
import time
import logging
import sys
import os
from datetime import datetime, timedelta
import pytz

# 로그 디렉토리 생성
log_dir = "/app/logs"
os.makedirs(log_dir, exist_ok=True)

# 한국 시간대 설정
KST = pytz.timezone('Asia/Seoul')

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(log_dir, "exporter.log")),
    ],
)
logger = logging.getLogger("music-bot-exporter")

# 메트릭 정의
TOTAL_PLAYS = Gauge("music_bot_total_plays", "Total number of plays from database")
SUCCESS_RATE = Gauge("music_bot_success_rate", "Success rate of plays from database")
UNIQUE_TRACKS = Gauge("music_bot_unique_tracks", "Number of unique tracks played")
UNIQUE_USERS = Gauge("music_bot_unique_users", "Number of unique users")
UNIQUE_SERVERS = Gauge("music_bot_unique_servers", "Number of unique servers")
HOURLY_PLAYS = Gauge("music_bot_hourly_plays", "Plays by hour of day", ["hour"])
SCRAPE_ERRORS = Counter(
    "music_bot_scrape_errors", "Number of errors during metrics collection"
)
LAST_SCRAPE_TIMESTAMP = Gauge(
    "music_bot_last_scrape_timestamp", "Timestamp of the last successful scrape"
)

# 캐시 변수들
last_update_time = None
cached_metrics = {
    "total_plays": 0,
    "successful_plays": 0,
    "unique_tracks": 0,
    "unique_users": 0,
    "unique_servers": 0,
    "hourly_plays": {str(hour): 0 for hour in range(24)}
}

# 모든 시간대에 대한 초기값 설정
def initialize_hourly_metrics():
    for hour in range(24):
        HOURLY_PLAYS.labels(hour=str(hour)).set(0)

# 데이터베이스 인덱스 확인 및 생성
def ensure_database_indexes():
    try:
        conn = sqlite3.connect("/app/musicbot/db/discord.db")
        cursor = conn.cursor()
        
        # 기존 인덱스 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_video_id'")
        if not cursor.fetchone():
            logger.info("video_id 인덱스 생성 중...")
            cursor.execute("CREATE INDEX idx_video_id ON statistics(video_id)")
            
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_user_id'")
        if not cursor.fetchone():
            logger.info("user_id 인덱스 생성 중...")
            cursor.execute("CREATE INDEX idx_user_id ON statistics(user_id)")
            
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_time'")
        if not cursor.fetchone():
            logger.info("time 인덱스 생성 중...")
            cursor.execute("CREATE INDEX idx_time ON statistics(time)")
            
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_created_at'")
        if not cursor.fetchone():
            logger.info("created_at 인덱스 생성 중...")
            cursor.execute("CREATE INDEX idx_created_at ON statistics(created_at)")
            
        conn.commit()
        logger.info("데이터베이스 인덱스 확인 완료")
    except Exception as e:
        logger.error(f"인덱스 생성 중 오류 발생: {str(e)}")
    finally:
        if conn:
            conn.close()

# 전체 메트릭 업데이트 (초기 실행 또는 주기적인 전체 갱신)
def update_all_metrics():
    global last_update_time
    try:
        conn = sqlite3.connect("/app/musicbot/db/discord.db")
        cursor = conn.cursor()
        
        # 단일 쿼리로 모든 기본 메트릭 가져오기
        cursor.execute("""
            SELECT 
                COUNT(*) as total_plays,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_plays,
                COUNT(DISTINCT video_id) as unique_tracks,
                COUNT(DISTINCT user_id) as unique_users,
                COUNT(DISTINCT guild_id) as unique_servers
            FROM statistics
        """)
        
        result = cursor.fetchone()
        if result:
            total_plays, successful_plays, unique_tracks, unique_users, unique_servers = result
            
            # 캐시 업데이트
            cached_metrics["total_plays"] = total_plays
            cached_metrics["successful_plays"] = successful_plays
            cached_metrics["unique_tracks"] = unique_tracks
            cached_metrics["unique_users"] = unique_users
            cached_metrics["unique_servers"] = unique_servers
            
            # 메트릭 설정
            TOTAL_PLAYS.set(total_plays)
            success_rate = (successful_plays / total_plays * 100) if total_plays > 0 else 0
            SUCCESS_RATE.set(success_rate)
            UNIQUE_TRACKS.set(unique_tracks)
            UNIQUE_USERS.set(unique_users)
            UNIQUE_SERVERS.set(unique_servers)
        
        # 시간대별 통계 (단일 쿼리)
        cursor.execute("""
            SELECT strftime('%H', time) as hour, COUNT(*) as count 
            FROM statistics 
            GROUP BY hour
        """)
        
        # 시간대별 통계 초기화 및 설정
        hourly_data = {str(hour): 0 for hour in range(24)}
        for row in cursor.fetchall():
            hour, count = row
            hourly_data[hour] = count
        
        # 캐시 업데이트
        cached_metrics["hourly_plays"] = hourly_data
        
        # 메트릭 설정
        initialize_hourly_metrics()
        for hour, count in hourly_data.items():
            HOURLY_PLAYS.labels(hour=hour).set(count)
        
        # 마지막 업데이트 시간 설정
        last_update_time = datetime.now(KST)
        LAST_SCRAPE_TIMESTAMP.set(last_update_time.timestamp())
        
        logger.info(f"전체 메트릭 업데이트 완료 - 총 재생: {total_plays}, 성공률: {success_rate:.1f}%")
        
    except Exception as e:
        SCRAPE_ERRORS.inc()
        logger.error(f"전체 메트릭 업데이트 중 오류 발생: {str(e)}")
    finally:
        if conn:
            conn.close()

# 증분 업데이트 (마지막 업데이트 이후 새 레코드만 처리)
def update_incremental_metrics():
    global last_update_time
    if not last_update_time:
        update_all_metrics()
        return
        
    try:
        # 마지막 업데이트 시간 이후의 레코드만 처리
        last_update_str = last_update_time.strftime("%Y-%m-%d %H:%M:%S")
        
        conn = sqlite3.connect("/app/musicbot/db/discord.db")
        cursor = conn.cursor()
        
        # 새 레코드 수 확인
        cursor.execute(f"SELECT COUNT(*) FROM statistics WHERE created_at > datetime('{last_update_str}')")
        new_records_count = cursor.fetchone()[0]
        
        if new_records_count == 0:
            logger.info("새로운 레코드가 없습니다. 메트릭 업데이트를 건너뜁니다.")
            # 마지막 스크랩 시간만 업데이트
            current_time = datetime.now(KST)
            LAST_SCRAPE_TIMESTAMP.set(current_time.timestamp())
            return
            
        logger.info(f"새로운 레코드 {new_records_count}개 발견, 증분 업데이트 수행 중...")
        
        # 새 레코드에 대한 통계 가져오기
        cursor.execute(f"""
            SELECT 
                COUNT(*) as new_total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as new_successful,
                COUNT(DISTINCT video_id) as new_videos,
                COUNT(DISTINCT user_id) as new_users,
                COUNT(DISTINCT guild_id) as new_servers
            FROM statistics 
            WHERE created_at > datetime('{last_update_str}')
        """)
        
        new_total, new_successful, new_videos, new_users, new_servers = cursor.fetchone()
        
        # 시간대별 새 통계
        cursor.execute(f"""
            SELECT strftime('%H', time) as hour, COUNT(*) as count 
            FROM statistics 
            WHERE created_at > datetime('{last_update_str}')
            GROUP BY hour
        """)
        
        new_hourly_data = {}
        for row in cursor.fetchall():
            hour, count = row
            new_hourly_data[hour] = count
        
        # 새로운 고유 항목 확인 (기존 캐시에 없는 항목만)
        cursor.execute(f"""
            SELECT COUNT(DISTINCT s1.video_id) 
            FROM statistics s1 
            WHERE s1.created_at > datetime('{last_update_str}') 
            AND NOT EXISTS (SELECT 1 FROM statistics s2 WHERE s2.video_id = s1.video_id AND s2.created_at <= datetime('{last_update_str}'))
        """)
        actual_new_videos = cursor.fetchone()[0]
        
        cursor.execute(f"""
            SELECT COUNT(DISTINCT s1.user_id) 
            FROM statistics s1 
            WHERE s1.created_at > datetime('{last_update_str}') 
            AND NOT EXISTS (SELECT 1 FROM statistics s2 WHERE s2.user_id = s1.user_id AND s2.created_at <= datetime('{last_update_str}'))
        """)
        actual_new_users = cursor.fetchone()[0]
        
        cursor.execute(f"""
            SELECT COUNT(DISTINCT s1.guild_id) 
            FROM statistics s1 
            WHERE s1.created_at > datetime('{last_update_str}') 
            AND NOT EXISTS (SELECT 1 FROM statistics s2 WHERE s2.guild_id = s1.guild_id AND s2.created_at <= datetime('{last_update_str}'))
        """)
        actual_new_servers = cursor.fetchone()[0]
        
        # 캐시 및 메트릭 업데이트
        cached_metrics["total_plays"] += new_total
        cached_metrics["successful_plays"] += new_successful
        cached_metrics["unique_tracks"] += actual_new_videos
        cached_metrics["unique_users"] += actual_new_users
        cached_metrics["unique_servers"] += actual_new_servers
        
        # 시간대별 통계 업데이트
        for hour, count in new_hourly_data.items():
            if hour in cached_metrics["hourly_plays"]:
                cached_metrics["hourly_plays"][hour] += count
            else:
                cached_metrics["hourly_plays"][hour] = count
        
        # 메트릭 설정
        TOTAL_PLAYS.set(cached_metrics["total_plays"])
        success_rate = (cached_metrics["successful_plays"] / cached_metrics["total_plays"] * 100) if cached_metrics["total_plays"] > 0 else 0
        SUCCESS_RATE.set(success_rate)
        UNIQUE_TRACKS.set(cached_metrics["unique_tracks"])
        UNIQUE_USERS.set(cached_metrics["unique_users"])
        UNIQUE_SERVERS.set(cached_metrics["unique_servers"])
        
        # 시간대별 메트릭 업데이트
        for hour, count in cached_metrics["hourly_plays"].items():
            HOURLY_PLAYS.labels(hour=hour).set(count)
        
        # 마지막 업데이트 시간 갱신
        global last_update_time
        last_update_time = datetime.now(KST)
        LAST_SCRAPE_TIMESTAMP.set(last_update_time.timestamp())
        
        logger.info(f"증분 메트릭 업데이트 완료 - 새 레코드: {new_records_count}, 총 재생: {cached_metrics['total_plays']}, 성공률: {success_rate:.1f}%")
        
    except Exception as e:
        SCRAPE_ERRORS.inc()
        logger.error(f"증분 메트릭 업데이트 중 오류 발생: {str(e)}")
    finally:
        if conn:
            conn.close()

# 메트릭 업데이트 함수 (전체 또는 증분)
def update_metrics_from_db():
    global last_update_time
    # 주기적으로 전체 메트릭을 갱신하고, 그 사이에는 증분 업데이트
    current_time = datetime.now(KST)
    
    # 처음 실행이거나 마지막 전체 업데이트로부터 1시간 이상 지났으면 전체 업데이트
    if not last_update_time or (current_time - last_update_time) > timedelta(hours=1):
        logger.info("전체 메트릭 업데이트 수행 중...")
        update_all_metrics()
    else:
        # 그 외에는 증분 업데이트
        update_incremental_metrics()


if __name__ == "__main__":
    # 메트릭 서버 시작
    start_http_server(8000)
    logger.info("메트릭 서버가 포트 8000에서 시작되었습니다")

    # 초기 시간대별 메트릭 초기화
    initialize_hourly_metrics()
    
    # 데이터베이스 인덱스 확인 및 생성
    ensure_database_indexes()
    
    # 초기 전체 메트릭 업데이트
    logger.info("초기 전체 메트릭 업데이트 수행 중...")
    update_all_metrics()

    # 주기적으로 메트릭 업데이트
    update_interval = 300  # 5분마다 업데이트
    logger.info(f"메트릭 업데이트 주기: {update_interval}초")
    
    while True:
        try:
            time.sleep(update_interval)
            update_metrics_from_db()
        except KeyboardInterrupt:
            logger.info("프로그램 종료 요청 감지. 종료합니다.")
            break
        except Exception as e:
            SCRAPE_ERRORS.inc()
            logger.error(f"예상치 못한 오류 발생: {str(e)}")
            # 오류 발생 시에도 계속 실행
