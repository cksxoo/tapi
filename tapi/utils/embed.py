import discord
from tapi.config import Development
from tapi.utils.language import get_lan

THEME_COLOR = Development.THEME_COLOR
APP_NAME_TAG_VER = f"{Development.APPLICATION_NAME} {Development.APP_TAG}"


def create_standard_embed(interaction_or_guild_id, title_key, description_key=None, color=THEME_COLOR):
    title = get_lan(interaction_or_guild_id, title_key)

    if description_key:
        description = get_lan(interaction_or_guild_id, description_key)
        embed = discord.Embed(title=title, description=description, color=color)
    else:
        embed = discord.Embed(title=title, color=color)

    embed.set_footer(text=APP_NAME_TAG_VER)
    return embed


def create_error_embed(error_message, color=THEME_COLOR):
    embed = discord.Embed(title=error_message, description="", color=color)
    embed.set_footer(text=APP_NAME_TAG_VER)
    return embed


async def send_embed(interaction, interaction_or_guild_id, title_key, description_key=None, color=THEME_COLOR, ephemeral=False):
    embed = create_standard_embed(interaction_or_guild_id, title_key, description_key, color)
    await interaction.response.send_message(embed=embed, ephemeral=ephemeral)


async def send_temp_embed(interaction, interaction_or_guild_id, title_key, description_key=None, color=THEME_COLOR, delete_after=3):
    embed = create_standard_embed(interaction_or_guild_id, title_key, description_key, color)
    await send_temp_message(interaction, embed, delete_after)


def format_text_with_limit(text: str, max_length: int) -> str:
    """텍스트를 제한된 길이로 포맷"""
    return text[:max_length] + "..." if len(text) > max_length else text


def get_track_thumbnail(track) -> str:
    """트랙의 썸네일 URL 가져오기 (Spotify, YouTube 등 모든 소스 지원)"""
    thumbnail_url = None

    # LavaSrc 플러그인이 제공하는 앨범 아트 (Spotify/Deezer/Apple Music 등)
    if hasattr(track, 'plugin_info') and track.plugin_info:
        if isinstance(track.plugin_info, dict):
            # LavaSrc의 albumArtUrl 필드 사용 (앨범 아트만, 아티스트 사진 제외)
            thumbnail_url = track.plugin_info.get('albumArtUrl') or track.plugin_info.get('artworkUrl')

    # 없으면 artwork_url 시도 (일부 버전에서 사용)
    if not thumbnail_url:
        if hasattr(track, 'artwork_url') and track.artwork_url:
            thumbnail_url = track.artwork_url
        elif hasattr(track, 'artworkUrl') and track.artworkUrl:
            thumbnail_url = track.artworkUrl

    # extra 필드 확인 (Lavalink v4 대체 방식)
    if not thumbnail_url and hasattr(track, 'extra') and track.extra:
        if isinstance(track.extra, dict):
            thumbnail_url = track.extra.get('albumArtUrl') or track.extra.get('artworkUrl')

    # YouTube 트랙 썸네일 (identifier가 YouTube ID인 경우)
    if not thumbnail_url and track.identifier:
        # Spotify/Deezer URI가 아닌 경우 YouTube 썸네일 사용
        if not any(x in track.uri for x in ['spotify.com', 'deezer.com', 'soundcloud.com', 'music.apple.com']):
            thumbnail_url = f"http://img.youtube.com/vi/{track.identifier}/0.jpg"

    return thumbnail_url


def create_track_embed(track, user_display_name: str) -> discord.Embed:
    """단일 트랙용 embed 생성"""
    embed = discord.Embed(color=THEME_COLOR)
    embed.description = f"**[{track.title}]({track.uri})** - {track.author}\nby {user_display_name}"

    # 썸네일 설정
    thumbnail_url = get_track_thumbnail(track)
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)

    embed.set_footer(text=APP_NAME_TAG_VER)
    return embed


def create_playlist_embed(interaction_or_guild_id, playlist_name: str, track_count: int) -> discord.Embed:
    """플레이리스트용 embed 생성"""
    embed = discord.Embed(color=THEME_COLOR)
    embed.title = get_lan(interaction_or_guild_id, "music_play_playlist")
    embed.description = f"**{playlist_name}** - {track_count} tracks {get_lan(interaction_or_guild_id, 'music_added_to_queue')}"
    embed.set_footer(text=APP_NAME_TAG_VER)
    return embed


async def send_temp_message(interaction, embed, delete_after=3, refresh_control=True):
    try:
        message = await interaction.followup.send(embed=embed)
        await message.delete(delay=delete_after)

        if refresh_control and hasattr(interaction, "guild") and interaction.guild:
            cog = interaction.client.get_cog("Music")
            if cog and hasattr(cog, "last_music_messages"):
                guild_id = interaction.guild.id
                if guild_id in cog.last_music_messages:
                    try:
                        player = interaction.client.lavalink.player_manager.get(guild_id)
                        if player and player.current:
                            old_message = cog.last_music_messages[guild_id]

                            from tapi.modules.player import MusicControlView
                            control_view = MusicControlView(cog, guild_id)

                            class FakeInteraction:
                                def __init__(self, user_id, guild_id, locale):
                                    self.user = type("obj", (object,), {"id": user_id})()
                                    self.guild = type("obj", (object,), {"id": guild_id})()
                                    self.locale = locale

                            # 현재 곡을 요청한 사람의 ID 사용, 명령어 실행한 사람의 언어로 표시
                            requester_id = player.current.requester if player.current else interaction.user.id
                            fake_interaction = FakeInteraction(requester_id, guild_id, interaction.locale)
                            updated_embed = control_view.update_embed_and_buttons(fake_interaction, player)

                            if updated_embed:
                                await old_message.edit(embed=updated_embed, view=control_view)
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        pass  # 메시지 업데이트 실패 시 무시
        return message
    except Exception:
        return None