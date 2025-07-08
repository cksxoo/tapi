from prometheus_client import start_http_server, Gauge, Counter
import sqlite3
import pandas as pd
import time
import logging
import sys
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/app/logs/exporter.log"),
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


# 모든 시간대에 대한 초기값 설정
def initialize_hourly_metrics():
    for hour in range(24):
        HOURLY_PLAYS.labels(hour=str(hour)).set(0)


def update_metrics_from_db():
    try:
        conn = sqlite3.connect("/app/musicbot/db/discord.db")

        # 전체 데이터를 로드하는 대신 집계 쿼리 사용
        total_plays = pd.read_sql_query(
            "SELECT COUNT(*) as count FROM statistics", conn
        ).iloc[0]["count"]
        successful_plays = pd.read_sql_query(
            "SELECT COUNT(*) as count FROM statistics WHERE success = 1", conn
        ).iloc[0]["count"]
        unique_tracks = pd.read_sql_query(
            "SELECT COUNT(DISTINCT video_id) as count FROM statistics", conn
        ).iloc[0]["count"]
        unique_users = pd.read_sql_query(
            "SELECT COUNT(DISTINCT user_id) as count FROM statistics", conn
        ).iloc[0]["count"]
        unique_servers = pd.read_sql_query(
            "SELECT COUNT(DISTINCT guild_id) as count FROM statistics", conn
        ).iloc[0]["count"]

        # 시간대별 통계
        hourly_df = pd.read_sql_query(
            "SELECT strftime('%H', time) as hour, COUNT(*) as count FROM statistics GROUP BY hour",
            conn,
        )

        conn.close()

        # 기본 통계 설정
        TOTAL_PLAYS.set(total_plays)
        success_rate = (successful_plays / total_plays * 100) if total_plays > 0 else 0
        SUCCESS_RATE.set(success_rate)
        UNIQUE_TRACKS.set(unique_tracks)
        UNIQUE_USERS.set(unique_users)
        UNIQUE_SERVERS.set(unique_servers)

        # 시간대별 통계 설정 (모든 시간대 초기화 후 데이터 있는 시간대만 업데이트)
        initialize_hourly_metrics()
        for _, row in hourly_df.iterrows():
            HOURLY_PLAYS.labels(hour=row["hour"]).set(row["count"])

        # 마지막 성공적인 스크랩 시간 기록
        LAST_SCRAPE_TIMESTAMP.set(datetime.now().timestamp())

        logger.info("메트릭 업데이트 완료")
    except Exception as e:
        SCRAPE_ERRORS.inc()
        logger.error(f"메트릭 업데이트 중 오류 발생: {str(e)}")


if __name__ == "__main__":
    # 메트릭 서버 시작
    start_http_server(8000)
    logger.info("메트릭 서버가 포트 8000에서 시작되었습니다")

    # 초기 시간대별 메트릭 초기화
    initialize_hourly_metrics()

    # 주기적으로 메트릭 업데이트
    while True:
        update_metrics_from_db()
        time.sleep(60)  # 1분마다 업데이트
