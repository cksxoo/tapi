import os
import json
import sqlite3
from contextlib import closing
from tapi.config import Development as Config


def get_lan(user_id, text: str):
    """user_id 가 선택한 언어를 반환"""
    default_language = "ko"
    
    with closing(sqlite3.connect(Config.DB_PATH)) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute(
                f"""
                SELECT * FROM language WHERE id=?
                """,
                (str(user_id),),
            )
            temp = cursor.fetchone()
            if temp is None:
                language = default_language
            else:
                language = temp[1]
                if not os.path.exists(f"tapi/languages/{language}.json"):
                    language = default_language

    # read language file
    with open(f"tapi/languages/{language}.json", encoding="utf-8") as f:
        language_data = json.load(f)
    return language_data[text]
