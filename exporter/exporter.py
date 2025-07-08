from prometheus_client import start_http_server, Gauge
import sqlite3
import pandas as pd
import time

# 메트릭 정의
TOTAL_PLAYS = Gauge("music_bot_total_plays", "Total number of plays from database")
SUCCESS_RATE = Gauge("music_bot_success_rate", "Success rate of plays from database")
UNIQUE_TRACKS = Gauge("music_bot_unique_tracks", "Number of unique tracks played")
UNIQUE_USERS = Gauge("music_bot_unique_users", "Number of unique users")
UNIQUE_SERVERS = Gauge("music_bot_unique_servers", "Number of unique servers")

# 시간대별 재생 통계를 위한 게이지 시리즈
HOURLY_PLAYS = Gauge("music_bot_hourly_plays", "Plays by hour of day", ["hour"])


def update_metrics_from_db():
    try:
        conn = sqlite3.connect("/app/musicbot/db/discord.db")
        df = pd.read_sql_query("SELECT * FROM statistics", conn)
        conn.close()

        if not df.empty:
            # 기본 통계
            total_plays = len(df)
            successful_plays = len(df[df["success"] == True])
            success_rate = (
                (successful_plays / total_plays * 100) if total_plays > 0 else 0
            )
            unique_tracks = df["video_id"].nunique()
            unique_users = df["user_id"].nunique()
            unique_servers = df["guild_id"].nunique()

            TOTAL_PLAYS.set(total_plays)
            SUCCESS_RATE.set(success_rate)
            UNIQUE_TRACKS.set(unique_tracks)
            UNIQUE_USERS.set(unique_users)
            UNIQUE_SERVERS.set(unique_servers)

            # 시간대별 통계
            df["hour"] = pd.to_datetime(df["time"], format="%H:%M:%S").dt.hour
            hourly_counts = df.groupby("hour").size().to_dict()

            for hour, count in hourly_counts.items():
                HOURLY_PLAYS.labels(hour=str(hour)).set(count)

        print("메트릭 업데이트 완료")
    except Exception as e:
        print(f"메트릭 업데이트 중 오류 발생: {str(e)}")


if __name__ == "__main__":
    # 메트릭 서버 시작
    start_http_server(8000)
    print("메트릭 서버가 포트 8000에서 시작되었습니다")

    # 주기적으로 메트릭 업데이트
    while True:
        update_metrics_from_db()
        time.sleep(60)  # 1분마다 업데이트
