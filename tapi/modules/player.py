import re
import traceback
from datetime import datetime
import pytz
import yt_dlp

import discord
from discord import app_commands

from discord.ext import commands  # Re-enabled this line

import lavalink
from lavalink.events import TrackStartEvent, QueueEndEvent, TrackExceptionEvent
from lavalink.errors import ClientError
from lavalink.server import LoadType

from tapi.utils.language import get_lan
from tapi.utils import volumeicon
from tapi import (
    LOGGER,
    CLIENT_ID,
    THEME_COLOR,
    APP_NAME_TAG_VER,
    HOST,
    PSW,
    REGION,
    PORT,
)
from tapi.utils.database import Database
from tapi.utils.statistics import Statistics

url_rx = re.compile(r"https?://(?:www\.)?.+")


class AudioConnection(discord.VoiceClient):
    """
    This is the preferred way to handle external voice sending
    This client will be created via a cls in the connect method of the channel
    see the following documentation:
    https://discordpy.readthedocs.io/en/latest/api.html#voiceprotocol
    """

    def __init__(self, client: discord.Client, channel: discord.abc.Connectable):
        self.client = client
        self.channel = channel
        self.guild_id = channel.guild.id
        self._destroyed = False

        if not hasattr(self.client, "lavalink"):
            # Instantiate a client if one doesn't exist.
            # We store it in `self.client` so that it may persist across cog reloads,
            # however this is not mandatory.
            self.client.lavalink = lavalink.Client(client.user.id)
            self.client.lavalink.add_node(
                host=HOST, port=PORT, password=PSW, region=REGION, name="default-node"
            )

        # Create a shortcut to the Lavalink client here.
        self.lavalink = self.client.lavalink

    async def on_voice_server_update(self, data):
        # the data needs to be transformed before being handed down to
        # voice_update_handler
        lavalink_data = {"t": "VOICE_SERVER_UPDATE", "d": data}
        await self.lavalink.voice_update_handler(lavalink_data)

    async def on_voice_state_update(self, data):
        channel_id = data["channel_id"]

        if not channel_id:
            await self._destroy()
            return

        self.channel = self.client.get_channel(int(channel_id))

        # the data needs to be transformed before being handed down to
        # voice_update_handler
        lavalink_data = {"t": "VOICE_STATE_UPDATE", "d": data}

        await self.lavalink.voice_update_handler(lavalink_data)

    async def connect(
        self,
        *,
        timeout: float,
        reconnect: bool,
        self_deaf: bool = False,
        self_mute: bool = False,
    ) -> None:
        """
        Connect the bot to the voice channel and create a player_manager
        if it doesn't exist yet.
        """
        # ensure there is a player_manager when creating a new voice_client
        self.lavalink.player_manager.create(guild_id=self.channel.guild.id)
        await self.channel.guild.change_voice_state(
            channel=self.channel, self_mute=self_mute, self_deaf=self_deaf
        )

    async def disconnect(self, *, force: bool = False) -> None:
        """
        Handles the disconnect.
        Cleans up running player and leaves the voice client.
        """
        player = self.lavalink.player_manager.get(self.channel.guild.id)

        if player is not None:
            # no need to disconnect if we are not connected
            if not force and not player.is_connected:
                return

            # None means disconnect
            await self.channel.guild.change_voice_state(channel=None)

            # update the channel_id of the player to None
            # this must be done because the on_voice_state_update that would set channel_id
            # to None doesn't get dispatched after the disconnect
            player.channel_id = None
            await self._destroy()

    async def _destroy(self):
        self.cleanup()

        if self._destroyed:
            # Idempotency handling, if `disconnect()` is called, the changed voice state
            # could cause this to run a second time.
            return

        self._destroyed = True

        try:
            await self.lavalink.player_manager.destroy(self.guild_id)
        except ClientError:
            pass


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if self.bot.lavalink and not hasattr(self.bot, "_event_hook_set"):
            self.bot.lavalink.add_event_hooks(self)
            self.bot._event_hook_set = True

    def cog_unload(self):
        """Cog unload handler. This removes any event hooks that were registered."""
        if self.bot.lavalink:
            self.bot.lavalink._event_hooks.clear()

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            embed = discord.Embed(
                title=error.original, description="", color=THEME_COLOR
            )
            embed.set_footer(text=APP_NAME_TAG_VER)
            await ctx.respond(embed=embed)
            # The above handles errors thrown in this cog and shows them to the user.
            # This shouldn't be a problem as the only errors thrown in this cog are from `ensure_voice`
            # which contain a reason string, such as "Join a voicechannel" etc. You can modify the above
            # if you want to do things differently.
        else:
            LOGGER.error(f"Unexpected error in cog_command_error: {traceback.format_exc()}")

    async def create_player(interaction: discord.Interaction):
        """
        A check that is invoked before any commands marked with `@app_commands.check(create_player)` can run.

        This function will try to create a player for the guild associated with this Interaction, or raise
        an error which will be relayed to the user if one cannot be created.
        """
        if interaction.guild is None:
            raise app_commands.NoPrivateMessage()

        try:
            player = interaction.client.lavalink.player_manager.create(
                interaction.guild.id
            )

            # 저장된 볼륨 설정 가져오기
            saved_volume = Database().get_volume(interaction.guild.id)
            await player.set_volume(saved_volume)

            # 저장된 반복 상태 설정
            loop = Database().get_loop(interaction.guild.id)
            if loop is not None:
                player.set_loop(loop)

            # 저장된 셔플 상태 설정
            shuffle = Database().get_shuffle(interaction.guild.id)
            if shuffle is not None:
                player.set_shuffle(shuffle)
        except Exception as e:
            LOGGER.error(f"Failed to create player: {e}")
            LOGGER.error(
                f"Lavalink connection details: HOST={HOST}, PORT={PORT}, REGION={REGION}"
            )
            raise
        # Create returns a player if one exists, otherwise creates.
        # This line is important because it ensures that a player always exists for a guild.

        # Most people might consider this a waste of resources for guilds that aren't playing, but this is
        # the easiest and simplest way of ensuring players are created.

        # These are commands that require the bot to join a voicechannel (i.e. initiating playback).
        # Commands such as volume/skip etc don't require the bot to be in a voicechannel so don't need listing here.
        should_connect = interaction.command.name in (
            "play",
            "scplay",
            "search",
            "connect",
        )

        voice_client = interaction.guild.voice_client

        if not interaction.user.voice or not interaction.user.voice.channel:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_not_in_voice_channel_title"),
                description=get_lan(
                    interaction.user.id, "music_not_in_voice_channel_description"
                ),
                color=THEME_COLOR,
            )
            embed.set_footer(
                text=get_lan(interaction.user.id, "music_not_in_voice_channel_footer")
                + "\n"
                + APP_NAME_TAG_VER
            )

            # 음성 채널 아이콘 이미지를 추가하여 시각적으로 더 명확하게 안내합니다
            embed.set_thumbnail(
                url="https://cdn.discordapp.com/attachments/1043307948483653642/1043308015911542794/headphones.png"
            )

            # 비동기 응답을 보내고 체크 실패를 발생시켜 명령어 실행을 중단합니다
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False

        voice_channel = interaction.user.voice.channel

        if voice_client is None:
            if not should_connect:
                raise app_commands.CheckFailure(
                    get_lan(interaction.user.id, "music_not_connected_voice_channel")
                )

            permissions = voice_channel.permissions_for(interaction.guild.me)

            if not permissions.connect or not permissions.speak:
                raise app_commands.CheckFailure(
                    get_lan(interaction.user.id, "music_no_permission")
                )

            if voice_channel.user_limit > 0:
                # A limit of 0 means no limit. Anything higher means that there is a member limit which we need to check.
                # If it's full, and we don't have "move members" permissions, then we cannot join it.
                if (
                    len(voice_channel.members) >= voice_channel.user_limit
                    and not interaction.guild.me.guild_permissions.move_members
                ):
                    raise app_commands.CheckFailure(
                        get_lan(interaction.user.id, "music_voice_channel_is_full")
                    )

            player.store("channel", interaction.channel.id)
            await interaction.user.voice.channel.connect(cls=AudioConnection)
        elif voice_client.channel.id != voice_channel.id:
            raise app_commands.CheckFailure(
                get_lan(interaction.user.id, "music_come_in_my_voice_channel")
            )

        return True

    @lavalink.listener(TrackStartEvent)
    async def on_track_start(self, event: TrackStartEvent):
        guild_id = event.player.guild_id
        channel_id = event.player.fetch("channel")
        guild = self.bot.get_guild(guild_id)

        if not guild:
            return await self.lavalink.player_manager.destroy(guild_id)

        channel = guild.get_channel(channel_id)
        player = self.bot.lavalink.player_manager.get(guild_id)
        track = event.track
        requester_id = track.requester

        # 통계 저장
        try:
            # 한국 시간대 설정
            kst = pytz.timezone('Asia/Seoul')
            now = datetime.now(kst)
            date = now.strftime("%Y-%m-%d")
            time = now.strftime("%H:%M:%S")
            requester = await self.bot.fetch_user(requester_id)
            user_name = requester.name if requester else "Unknown User"

            # duration을 밀리초에서 초로 변환
            duration_seconds = track.duration // 1000
            
            # created_at을 한국 시간대로 설정
            created_at = now.strftime("%Y-%m-%d %H:%M:%S")

            Database().set_statistics(
                date=date,
                time=time,
                guild_id=str(guild.id),
                guild_name=guild.name,
                channel_id=str(channel.id),
                channel_name=channel.name,
                user_id=str(requester_id),
                user_name=user_name,
                video_id=track.identifier,
                title=track.title,
                artist=track.author,
                duration=duration_seconds,
                success=True,
                created_at=created_at,
            )
        except Exception as e:
            LOGGER.error(f"Error saving statistics: {e}")

        if channel:
            embed = discord.Embed(color=THEME_COLOR)
            
            # 제목과 아티스트 정보 설정
            embed.title = (
                get_lan(requester_id, "music_now_playing")
                + "  💿 | "
                + track.author
            )
            embed.description = f"[{track.title}]({track.uri})"
            
            # 재생 시간 정보 추가
            embed.add_field(
                name=get_lan(requester_id, "music_length"),
                value=lavalink.format_time(track.duration),
            )
            
            # 셔플 상태 정보 추가
            embed.add_field(
                name=get_lan(requester_id, "music_shuffle"),
                value=(
                    get_lan(requester_id, "music_shuffle_already_on")
                    if player.shuffle
                    else get_lan(requester_id, "music_shuffle_already_off")
                ),
                inline=True,
            )
            
            # 반복 상태 정보 추가
            embed.add_field(
                name=get_lan(requester_id, "music_repeat"),
                value=[
                    get_lan(requester_id, "music_repeat_already_off"),
                    get_lan(requester_id, "music_repeat_already_one"),
                    get_lan(requester_id, "music_repeat_already_on"),
                ][player.loop],
                inline=True,
            )
            
            # 썸네일 이미지 추가 (YouTube 영상인 경우)
            if track.identifier:
                embed.set_thumbnail(url=f"http://img.youtube.com/vi/{track.identifier}/0.jpg")
                
            embed.set_footer(text=APP_NAME_TAG_VER)
            return await channel.send(embed=embed)

    @lavalink.listener(QueueEndEvent)
    async def on_queue_end(self, event: QueueEndEvent):
        guild_id = event.player.guild_id
        guild = self.bot.get_guild(guild_id)

        # Check if the voice client exists and if the player is connected
        if guild and guild.voice_client and event.player.is_connected:
            # Optional: Add a small delay if needed, or specific checks
            # before disconnecting.
            # For example, ensure the player is truly stopped or idle.
            try:
                await guild.voice_client.disconnect(force=True)
            except Exception as e:
                LOGGER.error(f"Error disconnecting voice client: {e}")

    @lavalink.listener(TrackExceptionEvent)
    async def on_track_exception(
        self, event: TrackExceptionEvent
    ):  # Corrected type hint
        original_track_uri = event.track.uri  # Defined original_track_uri
        original_track_title = event.track.title  # Defined original_track_title
        player = event.player  # Defined player
        requester = event.track.requester  # Define requester from event.track

        # The existing conditional block, with corrections
        if (
            "youtube.com/watch" in original_track_uri
            and event.severity
            in [
                "SUSPICIOUS",
                "COMMON",
                "FAULT",
            ]  # Changed from event.exception.severity
            and (
                "unavailable"
                in event.message.lower()  # Changed from event.exception.message
                or "copyright"
                in event.message.lower()  # Changed from event.exception.message
                or "playback on other websites has been disabled"
                in event.message.lower()  # Changed from event.exception.message
                or "requires payment"
                in event.message.lower()  # Changed from event.exception.message
            )
        ):

            LOGGER.info(
                f"Attempting yt-dlp fallback for failed track: {original_track_uri}"
            )
            try:
                ydl_opts = {
                    "format": "bestaudio/best",
                    "noplaylist": True,
                    "quiet": True,
                    "no_warnings": True,
                    "skip_download": True,
                    "source_address": "0.0.0.0",  # Ensure Lavalink can access if on different network interface
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(original_track_uri, download=False)

                stream_url_from_yt_dlp = None
                if info and "url" in info:
                    stream_url_from_yt_dlp = info["url"]
                elif (
                    info and info.get("entries") and info["entries"][0].get("url")
                ):  # Should not happen with noplaylist=True
                    stream_url_from_yt_dlp = info["entries"][0]["url"]

                if stream_url_from_yt_dlp:
                    LOGGER.info(
                        f"yt-dlp provided stream URL for '{original_track_title}': {stream_url_from_yt_dlp}"
                    )
                    new_results = await player.node.get_tracks(stream_url_from_yt_dlp)
                    if new_results and new_results.tracks:
                        new_track = new_results.tracks[0]
                        new_track.requester = requester  # Preserve original requester

                        # Add to front of queue. If player stopped due to exception, this should play next.
                        player.add(track=new_track, requester=requester, index=0)
                        LOGGER.info(
                            f"Added yt-dlp fallback track '{new_track.title}' to front of queue for guild {player.guild_id}."
                        )

                        # If player is not playing (e.g., exception stopped it and didn't auto-play next)
                        if (
                            not player.is_playing
                            and not player.paused
                            and player.is_connected
                        ):
                            await player.play()  # Start playing the new track
                        return  # yt-dlp fallback initiated
                    else:
                        LOGGER.warning(
                            f"yt-dlp got a stream URL, but Lavalink couldn't load it as a track: {stream_url_from_yt_dlp}"
                        )
                else:
                    LOGGER.warning(
                        f"yt-dlp did not find a streamable URL for: {original_track_uri}"
                    )

            except Exception as e:
                LOGGER.error(
                    f"yt-dlp fallback in on_track_exception failed for '{original_track_uri}': {e}"
                )

        # If fallback was not attempted or failed, send a message to the user
        channel_id = player.fetch("channel")  # 'player' is now correctly defined
        if channel_id:
            channel = self.bot.get_channel(int(channel_id))
            if channel:
                embed = discord.Embed(
                    title=get_lan(
                        requester or self.bot.user.id, "music_play_fail_title"
                    ),  # Use requester's language or default
                    description=get_lan(
                        requester or self.bot.user.id, "music_play_fail_description"
                    ).format(
                        track_title=original_track_title,
                        error_message=event.message,  # Changed from event.exception.message
                    ),
                    color=THEME_COLOR,
                )
                embed.set_footer(text=APP_NAME_TAG_VER)
                try:
                    await channel.send(embed=embed)
                except discord.HTTPException as e:
                    LOGGER.error(
                        f"Failed to send track exception message to channel {channel_id}: {e}"
                    )

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """
        음성 채널에서 사용자가 모두 나갔을 때 봇을 자동으로 연결 해제하는 기능
        """
        # 봇 자신의 음성 상태 변경은 무시
        if member.bot:
            return
        
        # 사용자가 음성 채널에서 나간 경우만 처리
        if before.channel and not after.channel:
            guild = before.channel.guild
            
            # 봇이 해당 길드의 음성 채널에 연결되어 있는지 확인
            if not guild.voice_client:
                return
            
            # 봇이 연결된 음성 채널 확인
            bot_voice_channel = guild.voice_client.channel
            
            # 사용자가 나간 채널이 봇이 있는 채널과 같은지 확인
            if before.channel != bot_voice_channel:
                return
            
            # 음성 채널에 남아있는 사용자 수 확인 (봇 제외)
            non_bot_members = [m for m in bot_voice_channel.members if not m.bot]
            
            # 봇만 남아있다면 연결 해제
            if len(non_bot_members) == 0:
                try:
                    # Lavalink 플레이어 정리
                    player = self.bot.lavalink.player_manager.get(guild.id)
                    if player:
                        await player.stop()
                        player.queue.clear()
                    
                    # 음성 채널에서 연결 해제
                    await guild.voice_client.disconnect(force=True)
                    
                    # 다국어 지원 로그 메시지 (기본값으로 한국어 사용)
                    log_message = get_lan(self.bot.user.id, "music_auto_disconnect_log").format(guild_name=guild.name)
                    LOGGER.info(log_message)
                    
                except Exception as e:
                    error_message = get_lan(self.bot.user.id, "music_auto_disconnect_error").format(error=str(e))
                    LOGGER.error(error_message)

    @app_commands.command(name="connect", description="Connect to voice channel!")
    @app_commands.check(create_player)
    async def connect(self, interaction: discord.Interaction):
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        if not player.is_connected:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_connect_voice_channel"),
                color=THEME_COLOR,
            )
            embed.set_footer(text=APP_NAME_TAG_VER)
            await interaction.response.send_message(embed=embed)
        embed = discord.Embed(
            title=get_lan(interaction.user.id, "music_already_connected_voice_channel"),
            color=THEME_COLOR,
        )
        embed.set_footer(text=APP_NAME_TAG_VER)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="play", description="Searches and plays a song from a given query."
    )
    @app_commands.describe(query="찾고싶은 음악의 제목이나 링크를 입력하세요")
    @app_commands.check(create_player)
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        try:
            # Get the player for this guild from cache.
            player = self.bot.lavalink.player_manager.get(interaction.guild.id)

            original_query_stripped = query.strip("<>")

            current_lavalink_query = original_query_stripped
            is_search_query = not url_rx.match(original_query_stripped)
            if is_search_query:
                current_lavalink_query = f"ytsearch:{original_query_stripped}"

            nofind = 0
            yt_dlp_attempted_for_url = (
                False  # Flag to ensure yt-dlp is tried only once for a failing URL
            )

            while True:
                results = await player.node.get_tracks(current_lavalink_query)

                if (
                    results.load_type == LoadType.EMPTY
                    or not results
                    or not results.tracks
                ):
                    if not is_search_query and not yt_dlp_attempted_for_url:
                        yt_dlp_attempted_for_url = True
                        LOGGER.info(
                            f"Lavalink failed for URL '{original_query_stripped}'. Trying yt-dlp."
                        )
                        try:
                            ydl_opts = {
                                "format": "bestaudio/best",
                                "noplaylist": True,
                                "quiet": True,
                                "no_warnings": True,
                                "skip_download": True,
                                "source_address": "0.0.0.0",  # Bind to all interfaces for Lavalink access
                            }
                            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                                info = ydl.extract_info(
                                    original_query_stripped, download=False
                                )

                                stream_url_from_yt_dlp = None
                                if (
                                    info and "url" in info
                                ):  # Direct stream URL from yt-dlp
                                    stream_url_from_yt_dlp = info["url"]
                                elif (
                                    info
                                    and info.get("entries")
                                    and info["entries"][0].get("url")
                                ):  # Fallback for some cases like playlist with noplaylist=True
                                    stream_url_from_yt_dlp = info["entries"][0]["url"]

                                if stream_url_from_yt_dlp:
                                    LOGGER.info(
                                        f"yt-dlp provided stream URL: {stream_url_from_yt_dlp}"
                                    )
                                    current_lavalink_query = stream_url_from_yt_dlp
                                    # Reset nofind for the new URL attempt, or just continue to retry with new query
                                    continue  # Retry the Lavalink get_tracks with the new yt-dlp URL
                                else:
                                    LOGGER.warning(
                                        f"yt-dlp did not find a streamable URL for: {original_query_stripped}"
                                    )
                        except Exception as e:
                            LOGGER.error(
                                f"Error during yt-dlp processing for '{original_query_stripped}': {e}"
                            )

                    # If yt-dlp was attempted and failed, or if it's a search query, handle retries/failure
                    if nofind < 3:
                        # If it was a URL and yt-dlp path was taken and failed to provide a new URL,
                        # we should not retry the original bad URL with Lavalink multiple times.
                        if not is_search_query and yt_dlp_attempted_for_url:
                            nofind = (
                                3  # Force failure after one yt-dlp attempt for a URL
                            )
                        else:
                            nofind += 1

                    if nofind >= 3:
                        embed = discord.Embed(
                            title=get_lan(
                                interaction.user.id, "music_can_not_find_anything"
                            ),
                            description=f"Query: {original_query_stripped}",  # Added original query for context
                            color=THEME_COLOR,
                        )
                        embed.set_footer(text=APP_NAME_TAG_VER)
                        return await interaction.followup.send(embed=embed)
                else:  # Lavalink found tracks
                    break

            # on_track_start에서 상세 정보를 표시하민로 간단한 메시지만 표시
            if results.load_type == LoadType.PLAYLIST:
                tracks = results.tracks
                trackcount = 0
                first_track = None

                for track in tracks:
                    try:
                        if trackcount != 1:
                            first_track = track
                            trackcount = 1

                        player.add(requester=interaction.user.id, track=track)
                    except Exception as e:
                        LOGGER.error(f"Error adding track from playlist: {e}")
                
                # 플레이리스트가 추가되었다는 메시지 표시
                embed = discord.Embed(color=THEME_COLOR)
                embed.title = get_lan(interaction.user.id, "music_play_playlist") + "  📑"
                embed.description = f"**{results.playlist_info.name}** - {len(tracks)} tracks {get_lan(interaction.user.id, 'music_added_to_queue')}"

            else:
                track = results.tracks[0]
                
                player.add(requester=interaction.user.id, track=track)
                
                # 단일 곡 추가 메시지 표시
                embed = discord.Embed(color=THEME_COLOR)
                embed.title = get_lan(interaction.user.id, "music_added_to_queue_title")
                embed.description = f"**[{track.title}]({track.uri})** - {track.author}"
            
            embed.set_footer(text=APP_NAME_TAG_VER)
            await interaction.followup.send(embed=embed)

            if not player.is_playing:
                await player.play()

        except Exception as e:
            LOGGER.error(f"Error in play command: {e}")
            try:
                # Record failed play attempt
                Statistics().record_play(
                    track=track if "track" in locals() else None,
                    guild_id=interaction.guild_id,
                    channel_id=interaction.channel_id,
                    user_id=interaction.user.id,
                    success=False,
                    interaction=interaction,
                )
            except Exception as stats_error:
                LOGGER.error(f"Failed to record failure statistics: {stats_error}")
            raise e

    @app_commands.command(
        name="scplay", description="Searches and plays a song from SoundCloud."
    )
    @app_commands.describe(
        query="SoundCloud에서 찾고싶은 음악의 제목이나 링크를 입력하세요"
    )
    @app_commands.check(create_player)
    async def scplay(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        # Get the player for this guild from cache.
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        # Remove leading and trailing <>. <> may be used to suppress embedding links in Discord.
        query = query.strip("<>")

        # Check if the user input might be a URL. If it isn't, we can Lavalink do a YouTube search for it instead.
        # SoundCloud searching is possible by prefixing "scsearch:" instead.
        if not url_rx.match(query):
            query = f"scsearch:{query}"

        nofind = 0
        while True:
            # Get the results for the query from Lavalink.
            results = await player.node.get_tracks(query)

            # Results could be None if Lavalink returns an invalid response (non-JSON/non-200 (OK)).
            # ALternatively, results['tracks'] could be an empty array if the query yielded no tracks.
            if results.load_type == LoadType.EMPTY or not results or not results.tracks:
                if nofind < 3:
                    nofind += 1
                elif nofind == 3:
                    embed = discord.Embed(
                        title=get_lan(
                            interaction.user.id, "music_can_not_find_anything"
                        ),
                        description="",
                        color=THEME_COLOR,
                    )
                    embed.set_footer(text=APP_NAME_TAG_VER)
                    return await interaction.followup.send(embed=embed)
            else:
                break

        # on_track_start에서 상세 정보를 표시하민로 간단한 메시지만 표시
        # Valid load_types are:
        #   TRACK    - direct URL to a track
        #   PLAYLIST - direct URL to playlist
        #   SEARCH   - query prefixed with either "ytsearch:" or "scsearch:". This could possibly be expanded with plugins.
        #   EMPTY    - no results for the query (result.tracks will be empty)
        #   ERROR    - the track encountered an exception during loading
        if results.load_type == LoadType.PLAYLIST:
            tracks = results.tracks
            trackcount = 0

            for track in tracks:
                if trackcount != 1:
                    trackcount = 1

                # Add all of the tracks from the playlist to the queue.
                player.add(requester=interaction.user.id, track=track)
            
            # 플레이리스트가 추가되었다는 메시지 표시
            embed = discord.Embed(color=THEME_COLOR)
            embed.title = get_lan(interaction.user.id, "music_play_playlist") + "  📑"
            embed.description = f"**{results.playlist_info.name}** - {len(tracks)} tracks {get_lan(interaction.user.id, 'music_added_to_queue')}"

        else:
            track = results.tracks[0]

            # You can attach additional information to audiotracks through kwargs, however this involves
            # constructing the AudioTrack class yourself.
            player.add(requester=interaction.user.id, track=track)
            
            # 단일 곡 추가 메시지 표시
            embed = discord.Embed(color=THEME_COLOR)
            embed.title = get_lan(interaction.user.id, "music_added_to_queue_title")
            embed.description = f"**[{track.title}]({track.uri})** - {track.author}"
        
        embed.set_footer(text=APP_NAME_TAG_VER)
        await interaction.followup.send(embed=embed)

        # We don't want to call .play() if the player is playing as that will effectively skip
        # the current track.
        if not player.is_playing:
            await player.play()

    @app_commands.command(
        name="search", description="Search for songs with a given keyword"
    )
    @app_commands.describe(query="Enter the keyword to search for songs")
    @app_commands.check(create_player)
    async def search(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        if not query:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_search_no_keyword"),
                color=THEME_COLOR,
            )
            embed.set_footer(text=APP_NAME_TAG_VER)
            return await interaction.followup.send(embed=embed)

        # Use ytsearch: prefix to search YouTube
        query = f"ytsearch:{query}"
        results = await player.node.get_tracks(query)

        if not results or not results.tracks:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_search_no_results"),
                color=THEME_COLOR,
            )
            embed.set_footer(text=APP_NAME_TAG_VER)
            return await interaction.followup.send(embed=embed)

        tracks = results.tracks[:5]  # Limit to 5 results

        embed = discord.Embed(
            title=get_lan(interaction.user.id, "music_search_results"),
            description=get_lan(interaction.user.id, "music_search_select"),
            color=THEME_COLOR,
        )
        for i, track in enumerate(tracks, start=1):
            embed.add_field(
                name=f"{i}. {track.title}",
                value=f"{track.author} - {lavalink.format_time(track.duration)}",
                inline=False,
            )
        embed.set_footer(text=APP_NAME_TAG_VER)

        view = SearchView(tracks, self, interaction)
        await interaction.followup.send(embed=embed, view=view)

    async def play_search_result(self, interaction: discord.Interaction, track):
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        player.add(requester=interaction.user.id, track=track)

        embed = discord.Embed(color=THEME_COLOR)
        embed.title = get_lan(interaction.user.id, "music_added_to_queue_title")
        embed.description = f"**[{track.title}]({track.uri})** - {track.author}"
        embed.set_footer(text=APP_NAME_TAG_VER)
        await interaction.followup.send(embed=embed, ephemeral=False)


        if not player.is_playing:
            await player.play()

    @app_commands.command(
        name="disconnect",
        description="Disconnects the player from the voice channel and clears its queue.",
    )
    @app_commands.check(create_player)
    async def disconnect(self, interaction: discord.Interaction):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        if not interaction.guild.voice_client:
            embed = discord.Embed(
                title=get_lan(
                    interaction.user.id, "music_dc_not_connect_voice_channel"
                ),
                color=THEME_COLOR,
            )
            embed.set_footer(text=APP_NAME_TAG_VER)
            return await interaction.followup.send(embed=embed)

        if not interaction.user.voice or (
            player.is_connected
            and interaction.user.voice.channel.id != int(player.channel_id)
        ):
            embed = discord.Embed(
                title=get_lan(
                    interaction.user.id, "music_dc_not_connect_my_voice_channel"
                ).format(name=interaction.user.name),
                color=THEME_COLOR,
            )
            embed.set_footer(text=APP_NAME_TAG_VER)
            return await interaction.followup.send(embed=embed)

        player.queue.clear()
        await player.stop()
        await interaction.guild.voice_client.disconnect(force=True)

        embed = discord.Embed(
            title=get_lan(interaction.user.id, "music_dc_disconnected"),
            color=THEME_COLOR,
        )
        embed.set_footer(text=APP_NAME_TAG_VER)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="skip", description="Skip to the next song!")
    @app_commands.check(create_player)
    async def skip(self, interaction: discord.Interaction):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        if not player.is_playing:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_not_playing"),
                description="",
                color=THEME_COLOR,
            )
            embed.set_footer(text=APP_NAME_TAG_VER)
            return await interaction.followup.send(embed=embed)

        await player.skip()

        embed = discord.Embed(
            title=get_lan(interaction.user.id, "music_skip_next"),
            description="",
            color=THEME_COLOR,
        )
        embed.set_footer(text=APP_NAME_TAG_VER)
        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="nowplaying", description="Sending the currently playing song!"
    )
    @app_commands.check(create_player)
    async def nowplaying(self, interaction: discord.Interaction):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        if not player.current:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_no_playing_music"),
                description="",
                color=THEME_COLOR,
            )
            embed.set_footer(text=APP_NAME_TAG_VER)
            return await interaction.followup.send(embed=embed)

        position = lavalink.utils.format_time(player.position)
        if player.current.stream:
            duration = "🔴 LIVE"
        else:
            duration = lavalink.utils.format_time(player.current.duration)
        song = f"**[{player.current.title}]({player.current.uri})**\n({position}/{duration})"
        embed = discord.Embed(
            color=THEME_COLOR,
            title=get_lan(interaction.user.id, "music_now_playing"),
            description=song,
        )

        embed.add_field(
            name=get_lan(interaction.user.id, "music_shuffle"),
            value=(
                get_lan(interaction.user.id, "music_shuffle_already_on")
                if player.shuffle
                else get_lan(interaction.user.id, "music_shuffle_already_off")
            ),
            inline=True,
        )
        embed.add_field(
            name=get_lan(interaction.user.id, "music_repeat"),
            value=[
                get_lan(interaction.user.id, "music_repeat_already_off"),
                get_lan(interaction.user.id, "music_repeat_already_one"),
                get_lan(interaction.user.id, "music_repeat_already_on"),
            ][player.loop],
            inline=True,
        )

        embed.set_thumbnail(
            url=f"{player.current.uri.replace('https://www.youtube.com/watch?v=', 'http://img.youtube.com/vi/')}/0.jpg"
        )
        embed.set_footer(text=APP_NAME_TAG_VER)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="queue", description="Send music queue!")
    @app_commands.check(create_player)
    async def queue(self, interaction: discord.Interaction):
        await interaction.response.defer()

        try:
            player = self.bot.lavalink.player_manager.get(interaction.guild.id)
            if not player.queue:
                embed = discord.Embed(
                    title=get_lan(
                        interaction.user.id, "music_no_music_in_the_playlist"
                    ),
                    description="",
                    color=THEME_COLOR,
                )
                embed.set_footer(text=APP_NAME_TAG_VER)
                return await interaction.followup.send(embed=embed)

            items_per_page = 10
            pages = [
                player.queue[i : i + items_per_page]
                for i in range(0, len(player.queue), items_per_page)
            ]

            class QueuePaginator(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=60)
                    self.current_page = 0

                @discord.ui.button(label="Previous", style=discord.ButtonStyle.gray)
                async def previous_page(
                    self,
                    button_interaction: discord.Interaction,
                    button: discord.ui.Button,
                ):
                    self.current_page = (self.current_page - 1) % len(pages)
                    await self.update_message(button_interaction)

                @discord.ui.button(label="Next", style=discord.ButtonStyle.gray)
                async def next_page(
                    self,
                    button_interaction: discord.Interaction,
                    button: discord.ui.Button,
                ):
                    self.current_page = (self.current_page + 1) % len(pages)
                    await self.update_message(button_interaction)

                async def update_message(self, button_interaction: discord.Interaction):
                    queue_list = ""
                    start_index = self.current_page * items_per_page
                    for index, track in enumerate(
                        pages[self.current_page], start=start_index + 1
                    ):
                        queue_list += f"`{index}.` [**{track.title}**]({track.uri})\n"
                    embed = discord.Embed(
                        description=get_lan(
                            button_interaction.user.id, "music_q"
                        ).format(lenQ=len(player.queue), queue_list=queue_list),
                        color=THEME_COLOR,
                    )
                    embed.set_footer(
                        text=f"{get_lan(button_interaction.user.id, 'music_page')} {self.current_page + 1}/{len(pages)}\n{APP_NAME_TAG_VER}"
                    )
                    await button_interaction.response.edit_message(
                        embed=embed, view=self
                    )

            view = QueuePaginator()
            queue_list = ""
            for index, track in enumerate(pages[0], start=1):
                queue_list += f"`{index}.` [**{track.title}**]({track.uri})\n"
            embed = discord.Embed(
                description=get_lan(interaction.user.id, "music_q").format(
                    lenQ=len(player.queue), queue_list=queue_list
                ),
                color=THEME_COLOR,
            )
            embed.set_footer(
                text=f"{get_lan(interaction.user.id, 'music_page')} 1/{len(pages)}\n{APP_NAME_TAG_VER}"
            )
            await interaction.followup.send(embed=embed, view=view)

        except Exception as e:
            error_embed = discord.Embed(
                title="Error",
                description=f"An error occurred while fetching the queue: {str(e)}",
                color=discord.Color.red(),
            )
            error_embed.set_footer(text=APP_NAME_TAG_VER)
            await interaction.followup.send(embed=error_embed)

    @app_commands.command(
        name="repeat", description="Repeat one song or repeat multiple songs!"
    )
    @app_commands.check(create_player)
    async def repeat(self, interaction: discord.Interaction):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        if not player.is_playing:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_not_playing"),
                description="",
                color=THEME_COLOR,
            )
            embed.set_footer(text=APP_NAME_TAG_VER)
            return await interaction.followup.send(embed=embed)

        if player.loop == 0:
            player.set_loop(2)
        elif player.loop == 2:
            player.set_loop(1)
        else:
            player.set_loop(0)

        Database().set_loop(interaction.guild.id, player.loop)

        embed = None
        if player.loop == 0:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_repeat_off"),
                description="",
                color=THEME_COLOR,
            )
        elif player.loop == 1:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_repeat_one"),
                description="",
                color=THEME_COLOR,
            )
        elif player.loop == 2:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_repeat_all"),
                description="",
                color=THEME_COLOR,
            )
        if embed is not None:
            embed.set_footer(text=APP_NAME_TAG_VER)
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="remove", description="Remove music from the playlist!")
    @app_commands.describe(
        index="Queue에서 제거하고 싶은 음악이 몇 번째 음악인지 입력해 주세요"
    )
    @app_commands.check(create_player)
    async def remove(self, interaction: discord.Interaction, index: int):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        if not player.queue:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_remove_no_wating_music"),
                description="",
                color=THEME_COLOR,
            )
            embed.set_footer(text=APP_NAME_TAG_VER)
            return await interaction.followup.send(embed=embed)
        if index > len(player.queue) or index < 1:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_remove_input_over").format(
                    last_queue=len(player.queue)
                ),
                description="",
                color=THEME_COLOR,
            )
            embed.set_footer(text=APP_NAME_TAG_VER)
            return await interaction.followup.send(embed=embed)
        removed = player.queue.pop(index - 1)  # Account for 0-index.
        embed = discord.Embed(
            title=get_lan(interaction.user.id, "music_remove_form_playlist").format(
                remove_music=removed.title
            ),
            description="",
            color=THEME_COLOR,
        )
        embed.set_footer(text=APP_NAME_TAG_VER)
        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="shuffle",
        description="The music in the playlist comes out randomly from the next song!",
    )
    @app_commands.check(create_player)
    async def shuffle(self, interaction: discord.Interaction):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        if not player.is_playing:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_not_playing"),
                description="",
                color=THEME_COLOR,
            )
            embed.set_footer(text=APP_NAME_TAG_VER)
            return await interaction.followup.send(embed=embed)

        player.set_shuffle(not player.shuffle)

        Database().set_shuffle(interaction.guild.id, player.shuffle)

        if player.shuffle:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_shuffle_on"),
                description="",
                color=THEME_COLOR,
            )
        else:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_shuffle_off"),
                description="",
                color=THEME_COLOR,
            )
        embed.set_footer(text=APP_NAME_TAG_VER)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="clear", description="Clear the music queue")
    @app_commands.check(create_player)
    async def clear(self, interaction: discord.Interaction):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        if not player.queue:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_no_music_in_queue"),
                description="",
                color=THEME_COLOR,
            )
            embed.set_footer(text=APP_NAME_TAG_VER)
            return await interaction.followup.send(embed=embed)

        queue_length = len(player.queue)
        player.queue.clear()

        embed = discord.Embed(
            title=get_lan(interaction.user.id, "music_queue_cleared"),
            description=get_lan(interaction.user.id, "music_queue_cleared_desc").format(count=queue_length),
            color=THEME_COLOR,
        )
        embed.set_footer(text=APP_NAME_TAG_VER)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="volume", description="Changes or display the volume")
    @app_commands.describe(volume="볼륨값을 입력하세요")
    @app_commands.check(create_player)
    async def volume(self, interaction: discord.Interaction, volume: int = None):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        if volume is None:
            volicon = await volumeicon(player.volume)
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_now_vol").format(
                    volicon=volicon, volume=player.volume
                ),
                description="",
                color=THEME_COLOR,
            )
            embed.set_footer(text=APP_NAME_TAG_VER)
            return await interaction.followup.send(embed=embed)

        if volume > 1000 or volume < 1:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_input_over_vol"),
                description=get_lan(interaction.user.id, "music_default_vol"),
                color=THEME_COLOR,
            )
            embed.set_footer(text=APP_NAME_TAG_VER)
            return await interaction.followup.send(embed=embed)

        await player.set_volume(volume)
        # 볼륨 설정을 DB에 저장
        Database().set_volume(interaction.guild.id, volume)

        volicon = await volumeicon(player.volume)
        embed = discord.Embed(
            title=get_lan(interaction.user.id, "music_set_vol").format(
                volicon=volicon, volume=player.volume
            ),
            description="",
            color=THEME_COLOR,
        )
        embed.set_footer(text=APP_NAME_TAG_VER)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="pause", description="Pause or resume music!")
    @app_commands.check(create_player)
    async def pause(self, interaction: discord.Interaction):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        if not player.is_playing:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_not_playing"),
                description="",
                color=THEME_COLOR,
            )
            embed.set_footer(text=APP_NAME_TAG_VER)
            return await interaction.followup.send(embed=embed)
        if player.paused:
            await player.set_pause(False)
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_resume"),
                description="",
                color=THEME_COLOR,
            )
            embed.set_footer(text=APP_NAME_TAG_VER)
            await interaction.followup.send(embed=embed)
        else:
            await player.set_pause(True)
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_pause"),
                description="",
                color=THEME_COLOR,
            )
            embed.set_footer(text=APP_NAME_TAG_VER)
            await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="seek",
        description="Adjust the music play time in seconds by the number after the command!",
    )
    @app_commands.describe(seconds="이동할 초를 입력하세요")
    async def seek(self, interaction: discord.Interaction, seconds: int):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        track_time = player.position + (seconds * 1000)
        await player.seek(track_time)
        embed = discord.Embed(
            title=get_lan(interaction.user.id, "music_seek_move_to").format(
                move_time=lavalink.utils.format_time(track_time)
            ),
            description="",
            color=THEME_COLOR,
        )
        embed.set_footer(text=APP_NAME_TAG_VER)
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Music(bot))
    LOGGER.info("Music loaded!")


class SearchSelect(discord.ui.Select):
    def __init__(self, tracks, cog, interaction):
        self.tracks = tracks
        self.cog = cog
        self.interaction = interaction
        options = [
            discord.SelectOption(
                label=f"{i+1}. {track.title[:50]}",
                description=f"{track.author} - {lavalink.format_time(track.duration)}",
                value=str(i),
            )
            for i, track in enumerate(tracks)
        ]
        super().__init__(
            placeholder=get_lan(interaction.user.id, "music_search_select_placeholder"),
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        selected_index = int(self.values[0])
        selected_track = self.tracks[selected_index]
        await self.cog.play_search_result(interaction, selected_track)


class SearchView(discord.ui.View):
    def __init__(self, tracks, cog, interaction):
        super().__init__()
        self.add_item(SearchSelect(tracks, cog, interaction))
