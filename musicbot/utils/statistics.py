"""

Table name example : date20220101

ID, video_id, count

"""

import re
import pymysql
import sqlite3
from contextlib import closing
from musicbot.config import Development as Config
from datetime import datetime, timedelta

url_rx = re.compile(r"(.+)?https?://(?:www\.)?.+")


class Statistics:
    def __init__(self):
        self.statisticsdb = StatisticsDb()

    def up(self, video_id: str) -> None:
        """비디오 재생 횟수를 1 증가시킵니다"""
        # 유튜브 비디오 ID가 아닌 링크라면
        if url_rx.match(video_id):
            return

        # Set table name
        date = datetime.today().strftime("%Y-%m-%d")
        # Get play count from db
        temp = self.statisticsdb.get(date, video_id)
        # Set count
        if temp is None:
            num = 1
        else:
            num = temp[2] + 1
        self.statisticsdb.write(date, video_id, num)

    def get_week(self) -> dict[str, int]:
        """이번주의 통계를 가져옵니다"""
        week_data = {}
        for day in range(7):  # 0 ~ 6
            # 타깃 날짜 설정
            target_date = datetime.today() - timedelta(days=day)
            date = target_date.strftime("%Y-%m-%d")

            # 해당 날짜의 데이터 가져오기
            videos_data = self.statisticsdb.get_all(date)
            if videos_data is not None:
                for data in videos_data:
                    _, video_id, count = data
                    week_data[video_id] = count

        return week_data


class StatisticsDb:
    def __init__(self):
        self.statistics = "statistics"

    def get(self, date: str, video_id: str) -> tuple[int, str, int] | None:
        """해당 날짜와 비디오 아이디로 데이터를 가져옴"""
        with closing(sqlite3.connect(Config.DB_PATH)) as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute(
                    f"SELECT * FROM {self.statistics} WHERE date=? AND video_id=?",
                    (date, video_id),
                )
                temp = cursor.fetchone()

                return temp

    def get_all(self, date: str) -> tuple[tuple[int, str, int]] | None:
        """해당 날짜의 모든 데이터를 가져옴"""
        with closing(sqlite3.connect(Config.DB_PATH)) as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute(
                    f"SELECT * FROM {self.statistics} WHERE date=? ORDER BY count DESC",
                    (date,),
                )
                temp = cursor.fetchall()

                return temp

    def write(self, date: str, video_id: str, edit_count: int = 1) -> None:
        # Create table if it doesn't exist
        with closing(sqlite3.connect(Config.DB_PATH)) as conn:
            if edit_count == 1:
                conn.execute(
                    f"CREATE TABLE IF NOT EXISTS {self.statistics} (date date, video_id text, count int)"
                )
                conn.commit()
            else:
                conn.execute(
                    f"UPDATE {self.statistics} SET count=%s WHERE video_id=%s AND date=%s",
                    (edit_count, video_id, date),
                )
                conn.commit()


if __name__ == "__main__":
    # For test
    statistics = Statistics()
    statistics.up("Youtube_video_id")
