from tapi.config import Development

THEME_COLOR = Development.THEME_COLOR
APP_NAME_TAG_VER = f"{Development.APPLICATION_NAME} {Development.APP_TAG}"


def format_text_with_limit(text: str, max_length: int) -> str:
    """텍스트를 제한된 길이로 포맷"""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3].rstrip() + "..."


def get_track_thumbnail(track) -> str:
    """트랙의 썸네일 URL 가져오기 (Spotify, YouTube 등 모든 소스 지원)"""
    thumbnail_url = None

    # LavaSrc 플러그인이 제공하는 앨범 아트 (Spotify/Deezer/Apple Music 등)
    if hasattr(track, "plugin_info") and track.plugin_info:
        if isinstance(track.plugin_info, dict):
            thumbnail_url = track.plugin_info.get(
                "albumArtUrl"
            ) or track.plugin_info.get("artworkUrl")

    # 없으면 artwork_url 시도 (일부 버전에서 사용)
    if not thumbnail_url:
        if hasattr(track, "artwork_url") and track.artwork_url:
            thumbnail_url = track.artwork_url
        elif hasattr(track, "artworkUrl") and track.artworkUrl:
            thumbnail_url = track.artworkUrl

    # extra 필드 확인 (Lavalink v4 대체 방식)
    if not thumbnail_url and hasattr(track, "extra") and track.extra:
        if isinstance(track.extra, dict):
            thumbnail_url = track.extra.get("albumArtUrl") or track.extra.get(
                "artworkUrl"
            )

    # YouTube 트랙 썸네일 (identifier가 YouTube ID인 경우)
    if not thumbnail_url and track.identifier:
        if not any(
            x in track.uri
            for x in ["spotify.com", "deezer.com", "soundcloud.com", "music.apple.com"]
        ):
            thumbnail_url = f"http://img.youtube.com/vi/{track.identifier}/0.jpg"

    return thumbnail_url
