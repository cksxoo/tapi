import os
import re
import sqlite3
from contextlib import closing
from datetime import datetime
import pandas as pd
from musicbot.config import Development as Config

url_rx = re.compile(r"(.+)?https?://(?:www\.)?.+")


class Statistics:
    def __init__(self):
        self.statistics = "statistics"

    def record_play(self, track, guild_id, channel_id, user_id, success=True):
        """트랙 재생 정보를 기록"""
        if track and url_rx.match(track.identifier):
            return
            
        now = datetime.now()
        
        data = {
            'date': now.strftime("%Y-%m-%d"),
            'time': now.strftime("%H:%M:%S"),
            'guild_id': str(guild_id),
            'channel_id': str(channel_id),
            'user_id': str(user_id),
            'video_id': track.identifier if track else None,
            'title': track.title if track else None,
            'artist': track.author if track else None,
            'duration': track.duration // 1000 if track else 0,  # milliseconds to seconds
            'success': success
        }
        
        self.insert_stats(data)

    def insert_stats(self, data: dict) -> None:
        """Insert statistics data"""
        with closing(sqlite3.connect(Config.DB_PATH)) as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute(
                    """
                INSERT INTO statistics 
                (date, time, guild_id, channel_id, user_id, video_id, 
                title, artist, duration, success)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        data.get("date", ""),
                        data.get("time", ""),
                        data.get("guild_id", ""),
                        data.get("channel_id", ""),
                        data.get("user_id", ""),
                        data.get("video_id", ""),
                        data.get("title", ""),
                        data.get("artist", ""),
                        data.get("duration", 0),
                        data.get("success", True),
                    ),
                )
                conn.commit()

    def get_stats(self, start_date=None, end_date=None, guild_id=None):
        """통계 조회"""
        query = "SELECT * FROM statistics WHERE 1=1"
        params = []

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        if guild_id:
            query += " AND guild_id = ?"
            params.append(str(guild_id))

        with closing(sqlite3.connect(Config.DB_PATH)) as conn:
            df = pd.read_sql_query(query, conn, params=params)
            return df