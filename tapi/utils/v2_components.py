import discord
from discord import ui

from tapi import (
    THEME_COLOR, APP_BANNER_URL, APP_NAME_TAG_VER, LOGGER,
    SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR, INFO_COLOR, MUSIC_COLOR,
)
from tapi.utils.language import get_lan
from tapi.utils.embed import get_track_thumbnail, format_text_with_limit


# ---- Shared Component Factories ----

def make_themed_container(*items, accent_color=THEME_COLOR, spoiler=False):
    """TAPI 테마 색상이 적용된 Container 생성"""
    return ui.Container(*items, accent_colour=accent_color, spoiler=spoiler)


def make_banner_gallery():
    """APP_BANNER_URL을 MediaGallery로 생성"""
    return ui.MediaGallery(discord.MediaGalleryItem(APP_BANNER_URL))


def make_separator(large=False):
    """구분선 생성"""
    spacing = discord.SeparatorSpacing.large if large else discord.SeparatorSpacing.small
    return ui.Separator(visible=True, spacing=spacing)


def make_invisible_spacer():
    """시각적 줄 없이 여백만 생성"""
    return ui.Separator(visible=False, spacing=discord.SeparatorSpacing.small)


def make_footer_text():
    """버전 정보 푸터 텍스트"""
    return ui.TextDisplay(f"-# {APP_NAME_TAG_VER}")


# ---- Progress Bar & Time Formatting ----

def format_ms_time(ms):
    """밀리초를 M:SS 또는 H:MM:SS 포맷으로 변환"""
    seconds = ms // 1000
    minutes = seconds // 60
    hours = minutes // 60
    if hours > 0:
        return f"{hours}:{minutes % 60:02d}:{seconds % 60:02d}"
    return f"{minutes}:{seconds % 60:02d}"


def make_progress_bar(current, total, length=16):
    """모던 thin-line 프로그레스 바 생성"""
    if total == 0:
        bar = "` " + "─" * length + " `"
        return bar, "`0:00` / `0:00`"
    ratio = current / total
    filled = int(ratio * length)
    if filled >= length:
        bar_chars = "━" * length
    else:
        bar_chars = "━" * filled + "●" + "─" * (length - filled - 1)
    bar = f"` {bar_chars} `"
    current_time = format_ms_time(current)
    total_time = format_ms_time(total)
    return bar, f"`{current_time}` / `{total_time}`"


# ---- Platform Emoji Helper ----

def get_platform_emoji(track):
    """트랙 URI 기반 플랫폼 이모지 반환"""
    if track.uri:
        if "spotify.com" in track.uri or "spotify:" in track.uri:
            return "<:spotify:1433358080208404511>"
        elif "soundcloud.com" in track.uri:
            return "<:soundcloud:1433358078199201874>"
        elif "youtube.com" in track.uri or "youtu.be" in track.uri:
            return "<:youtube:1433358082028863519>"
    return "🎵"


# ---- FakeInteraction (공통) ----

class FakeInteraction:
    """이벤트 핸들러에서 언어 키 조회용 가짜 interaction"""
    def __init__(self, user_id, guild_id, locale):
        self.user = type("obj", (object,), {"id": user_id})()
        self.guild = type("obj", (object,), {"id": guild_id})()
        self.locale = locale


# ---- StatusLayout (범용 상태 메시지) ----

STYLE_COLORS = {
    "default": THEME_COLOR,
    "success": SUCCESS_COLOR,
    "error": ERROR_COLOR,
    "warning": WARNING_COLOR,
    "info": INFO_COLOR,
    "music": MUSIC_COLOR,
}


class StatusLayout(ui.LayoutView):
    """범용 상태 메시지 V2 레이아웃"""
    def __init__(self, title_text=None, description_text=None, thumbnail_url=None,
                 accent_color=None, show_banner=False, show_footer=False, style="default"):
        super().__init__(timeout=None)

        if accent_color is None:
            accent_color = STYLE_COLORS.get(style, THEME_COLOR)

        items = []
        if title_text:
            items.append(ui.TextDisplay(f"**{title_text}**"))
        if description_text:
            if thumbnail_url:
                section = ui.Section(
                    ui.TextDisplay(description_text),
                    accessory=ui.Thumbnail(thumbnail_url),
                )
                items.append(section)
            else:
                items.append(ui.TextDisplay(description_text))
        if show_banner:
            items.append(make_separator())
            items.append(make_banner_gallery())
        if show_footer:
            items.append(make_separator())
            items.append(make_footer_text())

        self.add_item(make_themed_container(*items, accent_color=accent_color))


# ---- Track/Playlist/Error Layout Factories ----

def create_track_layout(track, user_display_name):
    """단일 트랙용 V2 레이아웃"""
    thumbnail_url = get_track_thumbnail(track)
    platform_emoji = get_platform_emoji(track)
    title = format_text_with_limit(track.title, 30)
    desc = f"{platform_emoji} **[{title}]({track.uri})**\n*{track.author}*\n-# Added by {user_display_name}"
    return StatusLayout(
        description_text=desc,
        thumbnail_url=thumbnail_url,
        style="success",
    )


def create_playlist_layout(interaction, playlist_name, track_count):
    """플레이리스트용 V2 레이아웃"""
    title = get_lan(interaction, "music_play_playlist")
    desc = f"**{playlist_name}** - {track_count} tracks {get_lan(interaction, 'music_added_to_queue')}"
    return StatusLayout(title_text=title, description_text=desc, style="success")


def create_error_layout(error_message):
    """에러 메시지 V2 레이아웃"""
    return StatusLayout(title_text=error_message, style="error")


# ---- send_temp_v2 (V2용 임시 메시지 전송) ----

async def send_temp_v2(interaction, layout_view, delete_after=3, refresh_control=True):
    """V2 임시 메시지 전송 (자동 삭제 설정에 따라)"""
    try:
        message = await interaction.followup.send(view=layout_view)
        
        # 설정 확인 후 삭제 여부 결정
        if interaction.guild:
            from tapi.utils.database import Database
            db = Database()
            if db.get_autodel(interaction.guild.id):
                await message.delete(delay=delete_after)
        else:
            await message.delete(delay=delete_after)

        if refresh_control and hasattr(interaction, "guild") and interaction.guild:
            await _refresh_now_playing(interaction)

        return message
    except Exception:
        return None


async def send_temp_status(interaction, key, delete_after=3, style="default", **format_kwargs):
    """언어 키로 V2 상태 메시지 전송"""
    text = get_lan(interaction, key)
    if format_kwargs:
        text = text.format(**format_kwargs)
    layout = StatusLayout(title_text=text, style=style)
    return await send_temp_v2(interaction, layout, delete_after)


# ---- Now Playing 패널 refresh 로직 ----

async def _refresh_now_playing(interaction):
    """Now Playing 패널을 현재 플레이어 상태로 갱신"""
    try:
        cog = interaction.client.get_cog("Music")
        if not cog or not hasattr(cog, "last_music_messages"):
            return

        guild_id = interaction.guild.id
        if guild_id not in cog.last_music_messages:
            return

        player = interaction.client.lavalink.player_manager.get(guild_id)
        if not player or not player.current:
            return

        old_message = cog.last_music_messages[guild_id]

        from tapi.modules.music_views import MusicControlLayout
        control_layout = MusicControlLayout(cog, guild_id)

        requester_id = player.current.requester if player.current else interaction.user.id
        user_locale = cog.user_locales.get(requester_id, 'en')
        fake_interaction = FakeInteraction(requester_id, guild_id, user_locale)
        control_layout.build_layout(fake_interaction, player)

        await old_message.edit(view=control_layout)
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        pass
    except Exception as e:
        LOGGER.debug(f"Error refreshing now playing panel: {e}")


async def sync_discord_message(bot, guild_id: int, command: str, user_id: int = 0):
    """웹 대시보드 명령 후 Discord Now Playing 메시지를 동기화합니다.

    - stop: 메시지 삭제
    - skip: on_track_start가 새 메시지를 보내므로 no-op
    - 나머지: 메시지 편집으로 상태 갱신
    """
    try:
        cog = bot.get_cog("Music")
        if not cog or not hasattr(cog, "last_music_messages"):
            return

        # stop: 메시지 삭제 + 참조 제거
        if command == "stop":
            if guild_id in cog.last_music_messages:
                try:
                    await cog.last_music_messages[guild_id].delete()
                except Exception:
                    pass
                finally:
                    cog.last_music_messages.pop(guild_id, None)
            return

        # skip: on_track_start가 새 메시지를 보내므로 여기서는 skip
        if command == "skip":
            return

        # 메시지가 없으면 할 일 없음
        if guild_id not in cog.last_music_messages:
            return

        player = bot.lavalink.player_manager.get(guild_id)
        if not player or not player.current:
            return

        # _refresh_now_playing과 동일한 패턴
        old_message = cog.last_music_messages[guild_id]

        from tapi.modules.music_views import MusicControlLayout
        control_layout = MusicControlLayout(cog, guild_id)

        requester_id = player.current.requester if player.current else user_id
        user_locale = cog.user_locales.get(requester_id, 'en')
        fake_interaction = FakeInteraction(requester_id, guild_id, user_locale)
        control_layout.build_layout(fake_interaction, player)

        await old_message.edit(view=control_layout)

    except (discord.NotFound, discord.Forbidden):
        # 메시지가 삭제되었거나 권한 없음 → stale 참조 제거
        cog = bot.get_cog("Music")
        if cog and hasattr(cog, "last_music_messages"):
            cog.last_music_messages.pop(guild_id, None)
    except discord.HTTPException:
        pass
    except Exception as e:
        LOGGER.debug(f"Error syncing discord message for web command '{command}': {e}")
