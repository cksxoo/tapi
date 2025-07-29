"""
loop:
    guild_id: int
    loop: int

shuffle:
    guild_id: int
    shuffle: int
"""

import os
import sqlite3
from contextlib import closing
from tapi.config import Development as Config
from tapi import LOGGER


class Database:
    def __init__(self):
        self.statistics = "statistics"
        self.language = "language"
        self.loop_table = "loop_setting"
        self.shuffle_table = "shuffle"

    def create_table(self) -> None:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(Config.DB_PATH), exist_ok=True)

        # Create the database
        with closing(sqlite3.connect(Config.DB_PATH)) as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute(
                    """
                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    time TEXT,
                    guild_id TEXT,
                    guild_name TEXT,
                    channel_id TEXT,
                    channel_name TEXT,
                    user_id TEXT,
                    user_name TEXT,
                    video_id TEXT,
                    title TEXT,
                    artist TEXT,
                    duration INTEGER,
                    success BOOLEAN,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
                )
                # 인덱스 생성
                cursor.execute(
                    """
                CREATE INDEX IF NOT EXISTS idx_date_guild 
                ON statistics(date, guild_id)
                """
                )

                # 스키마 마이그레이션 (컬럼 추가 및 순서 재정렬)
                cursor.execute("PRAGMA table_info(statistics)")
                current_columns = [info[1] for info in cursor.fetchall()]

                desired_order = [
                    'id', 'date', 'time', 'guild_id', 'guild_name', 'channel_id', 'channel_name',
                    'user_id', 'user_name', 'video_id', 'title', 'artist', 'duration', 'success', 'created_at'
                ]

                # 컬럼 순서가 다르거나 필요한 컬럼이 없으면 마이그레이션 진행
                if current_columns != desired_order:
                    # 임시 테이블 생성
                    cursor.execute("""
                    CREATE TABLE statistics_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT, time TEXT, guild_id TEXT, guild_name TEXT,
                        channel_id TEXT, channel_name TEXT, user_id TEXT, user_name TEXT,
                        video_id TEXT, title TEXT, artist TEXT, duration INTEGER,
                        success BOOLEAN, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """)

                    # 복사할 컬럼 결정 (기존 테이블과 새 테이블에 모두 있는 컬럼)
                    cols_to_copy = [col for col in desired_order if col in current_columns]

                    # 데이터 복사
                    cursor.execute(f"INSERT INTO statistics_new ({', '.join(cols_to_copy)}) SELECT {', '.join(cols_to_copy)} FROM statistics")

                    # 기존 테이블 삭제 및 이름 변경
                    cursor.execute("DROP TABLE statistics")
                    cursor.execute("ALTER TABLE statistics_new RENAME TO statistics")

                    # 인덱스 재생성
                    cursor.execute("DROP INDEX IF EXISTS idx_date_guild")
                    cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_date_guild 
                    ON statistics(date, guild_id)
                    """)
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS language (
                        id TEXT,
                        language TEXT
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS loop_setting (
                        guild_id TEXT,
                        loop_set INTEGER
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS shuffle (
                        guild_id TEXT,
                        shuffle INTEGER
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS volume (
                        guild_id TEXT PRIMARY KEY,
                        volume INTEGER
                    )
                    """
                )
                conn.commit()
            LOGGER.info("Database created successfully.")

    def set_statistics(
        self,
        date: str,
        time: str,
        guild_id: str,
        guild_name: str,
        channel_id: str,
        channel_name: str,
        user_id: str,
        user_name: str,
        video_id: str,
        title: str,
        artist: str,
        duration: int,
        success: bool,
        created_at: str = None,
    ) -> None:
        """통계 저장"""
        with closing(sqlite3.connect(Config.DB_PATH)) as conn:
            with closing(conn.cursor()) as cursor:
                if created_at:
                    # 명시적으로 created_at 값 제공
                    cursor.execute(
                        f"""INSERT INTO {self.statistics} (
                            date, time, guild_id, guild_name, channel_id, channel_name,
                            user_id, user_name, video_id, title, artist, duration, success, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            date,
                            time,
                            guild_id,
                            guild_name,
                            channel_id,
                            channel_name,
                            user_id,
                            user_name,
                            video_id,
                            title,
                            artist,
                            duration,
                            success,
                            created_at,
                        ),
                    )
                else:
                    # 기본값 사용 (기존 동작)
                    cursor.execute(
                        f"""INSERT INTO {self.statistics} (
                            date, time, guild_id, guild_name, channel_id, channel_name,
                            user_id, user_name, video_id, title, artist, duration, success
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            date,
                            time,
                            guild_id,
                            guild_name,
                            channel_id,
                            channel_name,
                            user_id,
                            user_name,
                            video_id,
                            title,
                            artist,
                            duration,
                            success,
                        ),
                    )
                conn.commit()

    def set_loop(self, guild_id: int, loop: int) -> None:
        """길드 아이디로 루프 저장"""
        with closing(sqlite3.connect(Config.DB_PATH)) as conn:
            with closing(conn.cursor()) as cursor:
                guild = str(guild_id)

                # read loop
                cursor.execute(
                    f"SELECT * FROM {self.loop_table} WHERE guild_id=?", (guild,)
                )
                db_loop = cursor.fetchone()
                if db_loop is None:
                    # add loop
                    cursor.execute(
                        f"INSERT INTO {self.loop_table} VALUES(?, ?)", (guild, loop)
                    )
                else:
                    # modify loop
                    cursor.execute(
                        f"UPDATE {self.loop_table} SET loop_set=? WHERE guild_id=?",
                        (loop, guild),
                    )

                conn.commit()

    def get_loop(self, guild_id: int) -> int | None:
        """모든 루프설정 가져오기"""
        with closing(sqlite3.connect(Config.DB_PATH)) as conn:
            with closing(conn.cursor()) as cursor:
                # read loop
                cursor.execute(
                    f"SELECT * FROM {self.loop_table} WHERE guild_id=?",
                    (str(guild_id),),
                )
                loop = cursor.fetchone()

                if loop is not None:
                    loop = loop[1]

                return loop

    def set_shuffle(self, guild_id: int, shuffle: bool) -> None:
        """길드 아이디로 셔플 저장"""
        with closing(sqlite3.connect(Config.DB_PATH)) as conn:
            with closing(conn.cursor()) as cursor:
                guild = str(guild_id)

                # read shuffle
                cursor.execute(
                    f"SELECT * FROM {self.shuffle_table} WHERE guild_id=?", (guild,)
                )
                db_shuffle = cursor.fetchone()
                if db_shuffle is None:
                    # add shuffle
                    cursor.execute(
                        f"INSERT INTO {self.shuffle_table} VALUES(?, ?)",
                        (guild, shuffle),
                    )
                else:
                    # modify shuffle
                    cursor.execute(
                        f"UPDATE {self.shuffle_table} SET shuffle=? WHERE guild_id=?",
                        (shuffle, guild),
                    )

                conn.commit()

    def get_shuffle(self, guild_id: int) -> bool | None:
        """모든 셔플설정 가져오기"""
        with closing(sqlite3.connect(Config.DB_PATH)) as conn:
            with closing(conn.cursor()) as cursor:
                # read shuffle
                cursor.execute(
                    f"SELECT * FROM {self.shuffle_table} WHERE guild_id=?",
                    (str(guild_id),),
                )
                shuffle = cursor.fetchone()

                if shuffle is not None:
                    shuffle = shuffle[1]

                return shuffle

    def set_volume(self, guild_id: int, volume: int) -> None:
        """길드별 볼륨 설정 저장"""
        with closing(sqlite3.connect(Config.DB_PATH)) as conn:
            with closing(conn.cursor()) as cursor:
                # 길드 ID를 문자열로 변환
                guild = str(guild_id)

                # 기존 볼륨 설정 확인
                cursor.execute("SELECT * FROM volume WHERE guild_id=?", (guild,))
                db_volume = cursor.fetchone()

                if db_volume is None:
                    # 새로운 볼륨 설정 추가
                    cursor.execute("INSERT INTO volume VALUES(?, ?)", (guild, volume))
                else:
                    # 기존 볼륨 설정 수정
                    cursor.execute(
                        "UPDATE volume SET volume=? WHERE guild_id=?", (volume, guild)
                    )
                conn.commit()

    def get_volume(self, guild_id: int) -> int:
        """길드별 볼륨 설정 가져오기"""
        with closing(sqlite3.connect(Config.DB_PATH)) as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute(
                    "SELECT volume FROM volume WHERE guild_id=?", (str(guild_id),)
                )
                result = cursor.fetchone()

                # 결과가 없으면 기본값 100 반환
                return result[0] if result else 20

    def set_user_language(self, user_id: int, language: str) -> None:
        """사용자 언어 설정 저장"""
        with closing(sqlite3.connect(Config.DB_PATH)) as conn:
            with closing(conn.cursor()) as cursor:
                user_id_str = str(user_id)
                
                # 기존 언어 설정 확인
                cursor.execute(
                    "SELECT * FROM language WHERE id=?", (user_id_str,)
                )
                existing = cursor.fetchone()
                
                if existing is None:
                    # 새로운 언어 설정 추가
                    cursor.execute(
                        "INSERT INTO language VALUES(?, ?)", (user_id_str, language)
                    )
                else:
                    # 기존 언어 설정 수정
                    cursor.execute(
                        "UPDATE language SET language=? WHERE id=?", (language, user_id_str)
                    )
                conn.commit()

    def get_user_language(self, user_id: int) -> str:
        """사용자 언어 설정 가져오기"""
        with closing(sqlite3.connect(Config.DB_PATH)) as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute(
                    "SELECT language FROM language WHERE id=?", (str(user_id),)
                )
                result = cursor.fetchone()
                
                # 기본 언어는 한국어
                return result[0] if result else "kr"
