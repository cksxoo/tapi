import os
import json
from tapi.utils.database import Database


def get_lan(guild_id, text: str):
    """길드 ID의 언어 설정을 반환
    
    Args:
        guild_id: 길드 ID (서버 언어 설정용)
        text: 번역할 텍스트 키
    """
    default_language = "ko"
    
    # Database에서 길드 언어 설정 조회
    db = Database()
    language = db.get_guild_language(guild_id)
    
    # 언어 파일이 존재하는지 확인
    if not os.path.exists(f"tapi/languages/{language}.json"):
        language = default_language

    # 언어 파일 읽기
    with open(f"tapi/languages/{language}.json", encoding="utf-8") as f:
        language_data = json.load(f)
    
    # 키가 없으면 기본값 반환
    return language_data.get(text, text)
