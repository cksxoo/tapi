import discord
from tapi.config import Development
from tapi.utils.language import get_lan

THEME_COLOR = Development.THEME_COLOR
APP_NAME_TAG_VER = f"{Development.APPLICATION_NAME} {Development.APP_TAG}"


def create_standard_embed(guild_id, title_key, description_key=None, color=THEME_COLOR):
    title = get_lan(guild_id, title_key)
    
    if description_key:
        description = get_lan(guild_id, description_key)
        embed = discord.Embed(title=title, description=description, color=color)
    else:
        embed = discord.Embed(title=title, color=color)
    
    embed.set_footer(text=APP_NAME_TAG_VER)
    return embed


def create_error_embed(error_message, color=THEME_COLOR):
    embed = discord.Embed(title=error_message, description="", color=color)
    embed.set_footer(text=APP_NAME_TAG_VER)
    return embed


async def send_embed(interaction, guild_id, title_key, description_key=None, color=THEME_COLOR, ephemeral=False):
    embed = create_standard_embed(guild_id, title_key, description_key, color)
    await interaction.response.send_message(embed=embed, ephemeral=ephemeral)


async def send_temp_embed(interaction, guild_id, title_key, description_key=None, color=THEME_COLOR, delete_after=3):
    embed = create_standard_embed(guild_id, title_key, description_key, color)
    await send_temp_message(interaction, embed, delete_after)


def format_text_with_limit(text: str, max_length: int) -> str:
    """텍스트를 제한된 길이로 포맷"""
    return text[:max_length] + "..." if len(text) > max_length else text


def create_track_embed(track, user_display_name: str) -> discord.Embed:
    """단일 트랙용 embed 생성"""
    embed = discord.Embed(color=THEME_COLOR)
    embed.description = f"**[{track.title}]({track.uri})** - {track.author}\nby {user_display_name}"
    
    if track.identifier:
        embed.set_thumbnail(
            url=f"http://img.youtube.com/vi/{track.identifier}/0.jpg"
        )
    
    embed.set_footer(text=APP_NAME_TAG_VER)
    return embed


def create_playlist_embed(guild_id: int, playlist_name: str, track_count: int) -> discord.Embed:
    """플레이리스트용 embed 생성"""
    embed = discord.Embed(color=THEME_COLOR)
    embed.title = get_lan(guild_id, "music_play_playlist")
    embed.description = f"**{playlist_name}** - {track_count} tracks {get_lan(guild_id, 'music_added_to_queue')}"
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
                                def __init__(self, user_id, guild_id):
                                    self.user = type("obj", (object,), {"id": user_id})()
                                    self.guild = type("obj", (object,), {"id": guild_id})()

                            fake_interaction = FakeInteraction(interaction.user.id, guild_id)
                            updated_embed = control_view.update_embed_and_buttons(fake_interaction, player)

                            if updated_embed:
                                await old_message.edit(embed=updated_embed, view=control_view)
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        pass  # 메시지 업데이트 실패 시 무시
        return message
    except Exception:
        return None