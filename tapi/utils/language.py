import os
import json


def get_lan(interaction, text: str):
    """사용자의 언어 설정을 Discord locale 기반으로 자동 감지하여 반환

    Args:
        interaction: discord.Interaction 객체
        text: 번역할 텍스트 키

    Returns:
        번역된 텍스트 (한국어/일본어/영어)
    """
    default_language = "en"  # 기본값은 영어

    # 사용자의 Discord locale 자동 감지
    if hasattr(interaction, 'locale'):
        user_locale = str(interaction.locale)
        if user_locale.startswith("ko"):
            language = "ko"
        elif user_locale.startswith("ja"):
            language = "ja"
        else:
            language = "en"
    else:
        # locale 속성이 없는 경우 기본값 사용
        language = default_language

    # 언어 파일이 존재하는지 확인
    if not os.path.exists(f"tapi/languages/{language}.json"):
        language = default_language

    # 언어 파일 읽기
    with open(f"tapi/languages/{language}.json", encoding="utf-8") as f:
        language_data = json.load(f)

    # 키가 없으면 기본값 반환
    return language_data.get(text, text)
