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

# 새로운 메트릭 추가
DAILY_PLAYS = Gauge("music_bot_daily_plays", "Plays in the last 24 hours")
WEEKLY_PLAYS = Gauge("music_bot_weekly_plays", "Plays in the last 7 days")
MONTHLY_PLAYS = Gauge("music_bot_monthly_plays", "Plays in the last 30 days")
TOP_TRACKS = Gauge("music_bot_top_tracks", "Most played tracks", ["video_id", "title"])
TOP_USERS = Gauge("music_bot_top_users", "Most active users", ["user_id"])
PLAYS_PER_HOUR = Gauge("music_bot_plays_per_hour", "Average plays per hour")
ACTIVE_SERVERS_TODAY = Gauge("music_bot_active_servers_today", "Servers active in the last 24 hours")
FAILED_PLAYS = Gauge("music_bot_failed_plays", "Number of failed plays")
AVERAGE_SESSION_LENGTH = Gauge("music_bot_avg_session_length", "Average session length in minutes")

SCRAPE_ERRORS = Counter(
    "music_bot_scrape_errors", "Number of errors during metrics collection"
)
LAST_SCRAPE_TIMESTAMP = Gauge(
    "music_bot_last_scrape_timestamp", "Timestamp of the last successful scrape"
)

class MetricsCollector:
    def __init__(self):
        self.last_update_time = None
        self.cached_metrics = {
            "total_plays": 0,
            "successful_plays": 0,
            "unique_tracks": 0,
            "unique_users": 0,
            "unique_servers": 0,
            "hourly_plays": {str(hour): 0 for hour in range(24)},
            "daily_plays": 0,
            "weekly_plays": 0,
            "monthly_plays": 0,
            "failed_plays": 0,
            "active_servers_today": 0
        }
    
    def initialize_hourly_metrics(self):
        """모든 시간대에 대한 초기값 설정"""
        for hour in range(24):
            HOURLY_PLAYS.labels(hour=str(hour)).set(0)

    def ensure_database_indexes(self):
        """데이터베이스 인덱스 확인 및 생성"""
        try:
            conn = sqlite3.connect("/app/musicbot/db/discord.db")
            cursor = conn.cursor()
            
            # 기존 인덱스 확인
            indexes_to_create = []
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_video_id'")
            if not cursor.fetchone():
                indexes_to_create.append(("idx_video_id", "CREATE INDEX idx_video_id ON statistics(video_id)"))
                
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_user_id'")
            if not cursor.fetchone():
                indexes_to_create.append(("idx_user_id", "CREATE INDEX idx_user_id ON statistics(user_id)"))
                
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_time'")
            if not cursor.fetchone():
                indexes_to_create.append(("idx_time", "CREATE INDEX idx_time ON statistics(time)"))
                
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_created_at'")
            if not cursor.fetchone():
                indexes_to_create.append(("idx_created_at", "CREATE INDEX idx_created_at ON statistics(created_at)"))
            
            if indexes_to_create:
                logger.info(f"생성이 필요한 인덱스: {[idx[0] for idx in indexes_to_create]}")
                
                for index_name, create_sql in indexes_to_create:
                    try:
                        logger.info(f"{index_name} 인덱스 생성 중...")
                        cursor.execute(create_sql)
                    except sqlite3.OperationalError as e:
                        if "readonly database" in str(e).lower():
                            logger.warning(f"데이터베이스가 읽기 전용입니다. {index_name} 인덱스 생성을 건너뜁니다.")
                        else:
                            logger.error(f"{index_name} 인덱스 생성 중 오류: {str(e)}")
                
                try:
                    conn.commit()
                    logger.info("데이터베이스 인덱스 생성 완료")
                except sqlite3.OperationalError as e:
                    if "readonly database" in str(e).lower():
                        logger.warning("데이터베이스가 읽기 전용입니다. 인덱스 생성 변경사항을 커밋할 수 없습니다.")
                    else:
                        logger.error(f"인덱스 커밋 중 오류: {str(e)}")
            else:
                logger.info("모든 필요한 인덱스가 이미 존재합니다.")
                
        except Exception as e:
            logger.error(f"인덱스 확인 중 오류 발생: {str(e)}")
        finally:
            if conn:
                conn.close()

    def update_all_metrics(self):
        """전체 메트릭 업데이트 (초기 실행 또는 주기적인 전체 갱신)"""
        try:
            conn = sqlite3.connect("/app/musicbot/db/discord.db")
            cursor = conn.cursor()
            
            # 단일 쿼리로 모든 기본 메트릭 가져오기
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_plays,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_plays,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_plays,
                    COUNT(DISTINCT video_id) as unique_tracks,
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(DISTINCT guild_id) as unique_servers
                FROM statistics
            """)
            
            result = cursor.fetchone()
            if result:
                total_plays, successful_plays, failed_plays, unique_tracks, unique_users, unique_servers = result
                
                # 캐시 업데이트
                self.cached_metrics["total_plays"] = total_plays
                self.cached_metrics["successful_plays"] = successful_plays
                self.cached_metrics["failed_plays"] = failed_plays
                self.cached_metrics["unique_tracks"] = unique_tracks
                self.cached_metrics["unique_users"] = unique_users
                self.cached_metrics["unique_servers"] = unique_servers
                
                # 메트릭 설정
                TOTAL_PLAYS.set(total_plays)
                FAILED_PLAYS.set(failed_plays)
                success_rate = (successful_plays / total_plays * 100) if total_plays > 0 else 0
                SUCCESS_RATE.set(success_rate)
                UNIQUE_TRACKS.set(unique_tracks)
                UNIQUE_USERS.set(unique_users)
                UNIQUE_SERVERS.set(unique_servers)
            
            # 시간별 통계
            current_time = datetime.now(KST)
            
            # 최근 24시간 재생 수
            cursor.execute("""
                SELECT COUNT(*) FROM statistics 
                WHERE datetime(created_at) >= datetime('now', '-1 day')
            """)
            daily_plays = cursor.fetchone()[0]
            self.cached_metrics["daily_plays"] = daily_plays
            DAILY_PLAYS.set(daily_plays)
            
            # 최근 7일 재생 수
            cursor.execute("""
                SELECT COUNT(*) FROM statistics 
                WHERE datetime(created_at) >= datetime('now', '-7 days')
            """)
            weekly_plays = cursor.fetchone()[0]
            self.cached_metrics["weekly_plays"] = weekly_plays
            WEEKLY_PLAYS.set(weekly_plays)
            
            # 최근 30일 재생 수
            cursor.execute("""
                SELECT COUNT(*) FROM statistics 
                WHERE datetime(created_at) >= datetime('now', '-30 days')
            """)
            monthly_plays = cursor.fetchone()[0]
            self.cached_metrics["monthly_plays"] = monthly_plays
            MONTHLY_PLAYS.set(monthly_plays)
            
            # 오늘 활성 서버 수
            cursor.execute("""
                SELECT COUNT(DISTINCT guild_id) FROM statistics 
                WHERE date(created_at) = date('now')
            """)
            active_servers_today = cursor.fetchone()[0]
            self.cached_metrics["active_servers_today"] = active_servers_today
            ACTIVE_SERVERS_TODAY.set(active_servers_today)
            
            # 시간당 평균 재생 수 (최근 24시간 기준)
            if daily_plays > 0:
                plays_per_hour = daily_plays / 24
                PLAYS_PER_HOUR.set(plays_per_hour)
            
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
            self.cached_metrics["hourly_plays"] = hourly_data
            
            # 메트릭 설정
            self.initialize_hourly_metrics()
            for hour, count in hourly_data.items():
                HOURLY_PLAYS.labels(hour=hour).set(count)
            
            # 인기 트랙 Top 5 (제목이 있는 경우만)
            cursor.execute("""
                SELECT video_id, title, COUNT(*) as play_count 
                FROM statistics 
                WHERE title IS NOT NULL AND title != '' 
                GROUP BY video_id, title 
                ORDER BY play_count DESC 
                LIMIT 5
            """)
            
            # 기존 top_tracks 메트릭 초기화
            TOP_TRACKS._metrics.clear()
            for row in cursor.fetchall():
                video_id, title, play_count = row
                # 제목이 너무 길면 잘라서 표시
                display_title = title[:50] + "..." if len(title) > 50 else title
                TOP_TRACKS.labels(video_id=video_id, title=display_title).set(play_count)
            
            # 활성 사용자 Top 5
            cursor.execute("""
                SELECT user_id, COUNT(*) as play_count 
                FROM statistics 
                GROUP BY user_id 
                ORDER BY play_count DESC 
                LIMIT 5
            """)
            
            # 기존 top_users 메트릭 초기화
            TOP_USERS._metrics.clear()
            for row in cursor.fetchall():
                user_id, play_count = row
                TOP_USERS.labels(user_id=str(user_id)).set(play_count)
            
            # 마지막 업데이트 시간 설정
            self.last_update_time = datetime.now(KST)
            LAST_SCRAPE_TIMESTAMP.set(self.last_update_time.timestamp())
            
            logger.info(f"전체 메트릭 업데이트 완료 - 총 재생: {total_plays}, 성공률: {success_rate:.1f}%, 일일 재생: {daily_plays}")
            
        except Exception as e:
            SCRAPE_ERRORS.inc()
            logger.error(f"전체 메트릭 업데이트 중 오류 발생: {str(e)}")
        finally:
            if conn:
                conn.close()

    def update_incremental_metrics(self):
        """증분 업데이트 (마지막 업데이트 이후 새 레코드만 처리)"""
        if not self.last_update_time:
            self.update_all_metrics()
            return
            
        try:
            # 마지막 업데이트 시간 이후의 레코드만 처리
            # KST 시간을 UTC로 변환 (SQLite는 UTC 기준으로 저장)
            last_update_utc = self.last_update_time.astimezone(pytz.UTC)
            last_update_str = last_update_utc.strftime("%Y-%m-%d %H:%M:%S")
            
            conn = sqlite3.connect("/app/musicbot/db/discord.db")
            cursor = conn.cursor()
            
            # 새 레코드 수 확인
            cursor.execute(f"SELECT COUNT(*) FROM statistics WHERE datetime(created_at) > datetime('{last_update_str}')")
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
                WHERE datetime(created_at) > datetime('{last_update_str}')
            """)
            
            new_total, new_successful, new_videos, new_users, new_servers = cursor.fetchone()
            
            # 시간대별 새 통계
            cursor.execute(f"""
                SELECT strftime('%H', time) as hour, COUNT(*) as count 
                FROM statistics 
                WHERE datetime(created_at) > datetime('{last_update_str}')
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
                WHERE datetime(s1.created_at) > datetime('{last_update_str}') 
                AND NOT EXISTS (SELECT 1 FROM statistics s2 WHERE s2.video_id = s1.video_id AND datetime(s2.created_at) <= datetime('{last_update_str}'))
            """)
            actual_new_videos = cursor.fetchone()[0]
            
            cursor.execute(f"""
                SELECT COUNT(DISTINCT s1.user_id) 
                FROM statistics s1 
                WHERE datetime(s1.created_at) > datetime('{last_update_str}') 
                AND NOT EXISTS (SELECT 1 FROM statistics s2 WHERE s2.user_id = s1.user_id AND datetime(s2.created_at) <= datetime('{last_update_str}'))
            """)
            actual_new_users = cursor.fetchone()[0]
            
            cursor.execute(f"""
                SELECT COUNT(DISTINCT s1.guild_id) 
                FROM statistics s1 
                WHERE datetime(s1.created_at) > datetime('{last_update_str}') 
                AND NOT EXISTS (SELECT 1 FROM statistics s2 WHERE s2.guild_id = s1.guild_id AND datetime(s2.created_at) <= datetime('{last_update_str}'))
            """)
            actual_new_servers = cursor.fetchone()[0]
            
            # 캐시 및 메트릭 업데이트
            self.cached_metrics["total_plays"] += new_total
            self.cached_metrics["successful_plays"] += new_successful
            self.cached_metrics["unique_tracks"] += actual_new_videos
            self.cached_metrics["unique_users"] += actual_new_users
            self.cached_metrics["unique_servers"] += actual_new_servers
            
            # 시간대별 통계 업데이트
            for hour, count in new_hourly_data.items():
                if hour in self.cached_metrics["hourly_plays"]:
                    self.cached_metrics["hourly_plays"][hour] += count
                else:
                    self.cached_metrics["hourly_plays"][hour] = count
            
            # 메트릭 설정
            TOTAL_PLAYS.set(self.cached_metrics["total_plays"])
            success_rate = (self.cached_metrics["successful_plays"] / self.cached_metrics["total_plays"] * 100) if self.cached_metrics["total_plays"] > 0 else 0
            SUCCESS_RATE.set(success_rate)
            UNIQUE_TRACKS.set(self.cached_metrics["unique_tracks"])
            UNIQUE_USERS.set(self.cached_metrics["unique_users"])
            UNIQUE_SERVERS.set(self.cached_metrics["unique_servers"])
            
            # 시간대별 메트릭 업데이트
            for hour, count in self.cached_metrics["hourly_plays"].items():
                HOURLY_PLAYS.labels(hour=hour).set(count)
            
            # 마지막 업데이트 시간 갱신
            self.last_update_time = datetime.now(KST)
            LAST_SCRAPE_TIMESTAMP.set(self.last_update_time.timestamp())
            
            # 디버그 로그 추가
            logger.debug(f"마지막 업데이트 시간: {self.last_update_time} (KST), UTC 변환: {self.last_update_time.astimezone(pytz.UTC)}")
            
            logger.info(f"증분 메트릭 업데이트 완료 - 새 레코드: {new_records_count}, 총 재생: {self.cached_metrics['total_plays']}, 성공률: {success_rate:.1f}%")
            
        except Exception as e:
            SCRAPE_ERRORS.inc()
            logger.error(f"증분 메트릭 업데이트 중 오류 발생: {str(e)}")
        finally:
            if conn:
                conn.close()

    def update_metrics_from_db(self):
        """메트릭 업데이트 함수 (전체 또는 증분)"""
        # 주기적으로 전체 메트릭을 갱신하고, 그 사이에는 증분 업데이트
        current_time = datetime.now(KST)
        
        # 처음 실행이거나 마지막 전체 업데이트로부터 1시간 이상 지났으면 전체 업데이트
        if not self.last_update_time or (current_time - self.last_update_time) > timedelta(hours=1):
            logger.info("전체 메트릭 업데이트 수행 중...")
            self.update_all_metrics()
        else:
            # 그 외에는 증분 업데이트
            self.update_incremental_metrics()




if __name__ == "__main__":
    # 메트릭 수집기 인스턴스 생성
    metrics_collector = MetricsCollector()
    
    # 메트릭 서버 시작
    start_http_server(8000)
    logger.info("메트릭 서버가 포트 8000에서 시작되었습니다")

    # 초기 시간대별 메트릭 초기화
    metrics_collector.initialize_hourly_metrics()
    
    # 데이터베이스 인덱스 확인 및 생성
    metrics_collector.ensure_database_indexes()
    
    # 초기 전체 메트릭 업데이트
    logger.info("초기 전체 메트릭 업데이트 수행 중...")
    metrics_collector.update_all_metrics()

    # 주기적으로 메트릭 업데이트
    update_interval = 300  # 5분마다 업데이트
    logger.info(f"메트릭 업데이트 주기: {update_interval}초")
    
    while True:
        try:
            time.sleep(update_interval)
            metrics_collector.update_metrics_from_db()
        except KeyboardInterrupt:
            logger.info("프로그램 종료 요청 감지. 종료합니다.")
            break
        except Exception as e:
            SCRAPE_ERRORS.inc()
            logger.error(f"예상치 못한 오류 발생: {str(e)}")
            # 오류 발생 시에도 계속 실행
