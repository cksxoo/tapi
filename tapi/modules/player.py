import re
import traceback
import yt_dlp

import discord
from discord import app_commands
from discord.ext import commands

import lavalink
from lavalink.server import LoadType

from tapi.utils.language import get_lan
from tapi import (
    LOGGER,
    THEME_COLOR,
    APP_NAME_TAG_VER,
    HOST,
    PSW,
    REGION,
    PORT,
)
from tapi.utils.database import Database
from tapi.utils.statistics import Statistics
from tapi.utils.embed import send_embed, send_temp_message, send_temp_embed

# 분리된 모듈들 import
from tapi.modules.audio_connection import AudioConnection
from tapi.modules.music_views import SearchView, MusicControlView
from tapi.modules.music_handlers import MusicHandlers

url_rx = re.compile(r"https?://(?:www\.)?.+")


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 길드별 마지막 음악 메시지를 저장하는 딕셔너리
        self.last_music_messages = {}
        # 핸들러 초기화
        self.handlers = MusicHandlers(self)

    @commands.Cog.listener()
    async def on_ready(self):
        if self.bot.lavalink and not hasattr(self.bot, "_event_hook_set"):
            self.bot.lavalink.add_event_hooks(self.handlers)
            self.bot._event_hook_set = True

    def cog_unload(self):
        """Cog unload handler. This removes any event hooks that were registered."""
        if self.bot.lavalink:
            self.bot.lavalink._event_hooks.clear()

    # 핸들러 메서드들을 위임
    async def _cleanup_music_message(self, guild_id: int, reason: str = "cleanup"):
        return await self.handlers._cleanup_music_message(guild_id, reason)

    async def _cleanup_player(
        self, guild_id: int, stop_current: bool = True, clear_queue: bool = True
    ):
        return await self.handlers._cleanup_player(guild_id, stop_current, clear_queue)

    async def _send_vote_message(
        self, guild_id: int, channel_id: int, user_id: int = None
    ):
        return await self.handlers._send_vote_message(guild_id, channel_id, user_id)

    async def _full_disconnect_cleanup(
        self,
        guild_id: int,
        reason: str = "disconnect",
        send_vote: bool = False,
        channel_id: int = None,
        user_id: int = None,
    ):
        return await self.handlers._full_disconnect_cleanup(
            guild_id, reason, send_vote, channel_id, user_id
        )

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        return await self.handlers.on_voice_state_update(member, before, after)

    @staticmethod
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

        # Commands that require the bot to join a voicechannel
        should_connect = interaction.command.name in (
            "play",
            "scplay",
            "search",
            "connect",
        )

        voice_client = interaction.guild.voice_client

        if not interaction.user.voice or not interaction.user.voice.channel:
            embed = discord.Embed(
                title=get_lan(interaction.guild.id, "music_not_in_voice_channel_title"),
                description=get_lan(
                    interaction.guild.id, "music_not_in_voice_channel_description"
                ),
                color=THEME_COLOR,
            )
            embed.set_footer(
                text=get_lan(interaction.guild.id, "music_not_in_voice_channel_footer")
                + "\n"
                + APP_NAME_TAG_VER
            )

            embed.set_thumbnail(
                url="https://cdn.discordapp.com/attachments/1043307948483653642/1043308015911542794/headphones.png"
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
            raise app_commands.CheckFailure("User not in voice channel")

        voice_channel = interaction.user.voice.channel

        if voice_client is None:
            if not should_connect:
                raise app_commands.CheckFailure(
                    get_lan(interaction.guild.id, "music_not_connected_voice_channel")
                )

            permissions = voice_channel.permissions_for(interaction.guild.me)

            if not permissions.connect or not permissions.speak:
                await send_temp_embed(
                    interaction, interaction.guild.id, "music_no_permission"
                )
                raise app_commands.CheckFailure(
                    get_lan(interaction.guild.id, "music_no_permission")
                )

            if voice_channel.user_limit > 0:
                if (
                    len(voice_channel.members) >= voice_channel.user_limit
                    and not interaction.guild.me.guild_permissions.move_members
                ):
                    raise app_commands.CheckFailure(
                        get_lan(interaction.guild.id, "music_voice_channel_is_full")
                    )

            player.store("channel", interaction.channel.id)
            await interaction.user.voice.channel.connect(cls=AudioConnection)
        elif voice_client.channel.id != voice_channel.id:
            raise app_commands.CheckFailure(
                get_lan(interaction.guild.id, "music_come_in_my_voice_channel")
            )

        return True

    @app_commands.command(name="connect", description="Connect to voice channel!")
    @app_commands.check(create_player)
    async def connect(self, interaction: discord.Interaction):
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        if not player.is_connected:
            await send_embed(
                interaction, interaction.guild.id, "music_connect_voice_channel"
            )
        else:
            await send_embed(
                interaction,
                interaction.guild.id,
                "music_already_connected_voice_channel",
            )

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
            else:
                # URL인 경우 list 파라미터 제거 (단일 곡 재생을 위해)
                if (
                    "youtube.com" in original_query_stripped
                    or "youtu.be" in original_query_stripped
                ):
                    # list 파라미터와 관련 파라미터들 제거
                    current_lavalink_query = re.sub(
                        r"[&?]list=[^&]*", "", original_query_stripped
                    )
                    current_lavalink_query = re.sub(
                        r"[&?]index=[^&]*", "", current_lavalink_query
                    )
                    # URL 정리 (연속된 &나 ?& 패턴 수정)
                    current_lavalink_query = re.sub(
                        r"[&?]+",
                        lambda m: (
                            "?"
                            if m.start() == original_query_stripped.find("?")
                            else "&"
                        ),
                        current_lavalink_query,
                    )
                    current_lavalink_query = current_lavalink_query.rstrip("&?")

            nofind = 0
            yt_dlp_attempted_for_url = False

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
                                "source_address": "0.0.0.0",
                            }
                            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                                info = ydl.extract_info(
                                    original_query_stripped, download=False
                                )

                                stream_url_from_yt_dlp = None
                                if info and "url" in info:
                                    stream_url_from_yt_dlp = info["url"]
                                elif (
                                    info
                                    and info.get("entries")
                                    and info["entries"][0].get("url")
                                ):
                                    stream_url_from_yt_dlp = info["entries"][0]["url"]

                                if stream_url_from_yt_dlp:
                                    LOGGER.info(
                                        f"yt-dlp provided stream URL: {stream_url_from_yt_dlp}"
                                    )
                                    current_lavalink_query = stream_url_from_yt_dlp
                                    continue
                                else:
                                    LOGGER.warning(
                                        f"yt-dlp did not find a streamable URL for: {original_query_stripped}"
                                    )
                        except Exception as e:
                            LOGGER.error(
                                f"Error during yt-dlp processing for '{original_query_stripped}': {e}"
                            )

                    if nofind < 3:
                        if not is_search_query and yt_dlp_attempted_for_url:
                            nofind = 3
                        else:
                            nofind += 1

                    if nofind >= 3:
                        embed = discord.Embed(
                            title=get_lan(
                                interaction.guild.id, "music_can_not_find_anything"
                            ),
                            description=f"Query: {original_query_stripped}",
                            color=THEME_COLOR,
                        )
                        embed.set_footer(text=APP_NAME_TAG_VER)
                        return await send_temp_message(interaction, embed)
                else:
                    break

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

                embed = discord.Embed(color=THEME_COLOR)
                embed.title = get_lan(interaction.guild.id, "music_play_playlist")
                embed.description = f"**{results.playlist_info.name}** - {len(tracks)} tracks {get_lan(interaction.guild.id, 'music_added_to_queue')}"

            else:
                track = results.tracks[0]

                player.add(requester=interaction.user.id, track=track)

                embed = discord.Embed(color=THEME_COLOR)
                embed.description = f"**[{track.title}]({track.uri})** - {track.author}\nby {interaction.user.display_name}"

                if track.identifier:
                    embed.set_thumbnail(
                        url=f"http://img.youtube.com/vi/{track.identifier}/0.jpg"
                    )

            await send_temp_message(interaction, embed)

            if not player.is_playing:
                await player.play()

        except Exception as e:
            LOGGER.error(f"Error in play command: {e}")
            try:
                Statistics().record_play(
                    track=track if "track" in locals() else None,
                    guild_id=interaction.guild_id,
                    channel_id=interaction.channel_id,
                    user_id=interaction.guild.id,
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

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        query = query.strip("<>")

        if not url_rx.match(query):
            query = f"scsearch:{query}"

        nofind = 0
        while True:
            results = await player.node.get_tracks(query)

            if results.load_type == LoadType.EMPTY or not results or not results.tracks:
                if nofind < 3:
                    nofind += 1
                elif nofind == 3:
                    embed = discord.Embed(
                        title=get_lan(
                            interaction.guild.id, "music_can_not_find_anything"
                        ),
                        description="",
                        color=THEME_COLOR,
                    )
                    embed.set_footer(text=APP_NAME_TAG_VER)
                    return await send_temp_message(interaction, embed)
            else:
                break

        if results.load_type == LoadType.PLAYLIST:
            tracks = results.tracks
            trackcount = 0

            for track in tracks:
                if trackcount != 1:
                    trackcount = 1

                player.add(requester=interaction.user.id, track=track)

            embed = discord.Embed(color=THEME_COLOR)
            embed.title = get_lan(interaction.guild.id, "music_play_playlist")
            embed.description = f"**{results.playlist_info.name}** - {len(tracks)} tracks {get_lan(interaction.guild.id, 'music_added_to_queue')}"

        else:
            track = results.tracks[0]
            player.add(requester=interaction.user.id, track=track)

            embed = discord.Embed(color=THEME_COLOR)
            embed.description = f"**[{track.title}]({track.uri})** - {track.author}\nby {interaction.user.display_name}"

            if track.identifier:
                if "soundcloud.com" in track.uri:
                    embed.set_thumbnail(url=track.uri)
                else:
                    embed.set_thumbnail(
                        url=f"http://img.youtube.com/vi/{track.identifier}/0.jpg"
                    )

        await send_temp_message(interaction, embed)

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
            return await send_temp_embed(
                interaction, interaction.guild.id, "music_search_no_keyword"
            )

        query = f"ytsearch:{query}"
        results = await player.node.get_tracks(query)

        if not results or not results.tracks:
            return await send_temp_embed(
                interaction, interaction.guild.id, "music_search_no_results"
            )

        tracks = results.tracks[:5]

        embed = discord.Embed(
            title=get_lan(interaction.guild.id, "music_search_results"),
            description=get_lan(interaction.guild.id, "music_search_select"),
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
        message = await interaction.followup.send(embed=embed, view=view)
        view.message = message

    async def play_search_result(self, interaction: discord.Interaction, track):
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        player.add(requester=interaction.user.id, track=track)

        embed = discord.Embed(color=THEME_COLOR)
        embed.description = f"**[{track.title}]({track.uri})** - {track.author}\nby {interaction.user.display_name}"

        if track.identifier:
            embed.set_thumbnail(
                url=f"http://img.youtube.com/vi/{track.identifier}/0.jpg"
            )

        await send_temp_message(interaction, embed)

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
                    interaction.guild.id, "music_dc_not_connect_voice_channel"
                ),
                color=THEME_COLOR,
            )
            embed.set_footer(text=APP_NAME_TAG_VER)
            return await send_temp_message(interaction, embed)

        if not interaction.user.voice or (
            player.is_connected
            and interaction.user.voice.channel.id != int(player.channel_id)
        ):
            embed = discord.Embed(
                title=get_lan(
                    interaction.guild.id, "music_dc_not_connect_my_voice_channel"
                ).format(name=interaction.user.name),
                color=THEME_COLOR,
            )
            embed.set_footer(text=APP_NAME_TAG_VER)
            return await send_temp_message(interaction, embed)

        guild_id = interaction.guild.id
        await self._full_disconnect_cleanup(
            guild_id,
            "manual_disconnect",
            send_vote=True,
            channel_id=interaction.channel.id,
            user_id=interaction.guild.id,
        )

        await send_temp_embed(interaction, interaction.guild.id, "music_dc_disconnected")

    @app_commands.command(name="skip", description="Skip to the next song!")
    @app_commands.check(create_player)
    async def skip(self, interaction: discord.Interaction):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        if not player.is_playing:
            return await send_temp_embed(
                interaction, interaction.guild.id, "music_not_playing"
            )

        # 한 곡 반복모드일 때는 전체 반복으로 전환 후 skip
        if player.loop == 1:  # 한 곡 반복모드
            player.set_loop(2)  # 전체 반복으로 전환
            Database().set_loop(interaction.guild.id, 2)  # 설정 저장
            
        await player.skip()
        await send_temp_embed(interaction, interaction.guild.id, "music_skip_next")

    @app_commands.command(
        name="nowplaying", description="Sending the currently playing song!"
    )
    @app_commands.check(create_player)
    async def nowplaying(self, interaction: discord.Interaction):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        if not player.current:
            embed = discord.Embed(
                title=get_lan(interaction.guild.id, "music_no_playing_music"),
                description="",
                color=THEME_COLOR,
            )
            embed.set_footer(text=APP_NAME_TAG_VER)
            return await send_temp_message(interaction, embed)

        # 기존 음악 메시지 삭제
        await self._cleanup_music_message(interaction.guild.id, "nowplaying_command")

        # 새로운 컨트롤 패널 생성
        control_view = MusicControlView(self, interaction.guild.id)

        # 가짜 interaction 객체 생성 (언어 설정을 위해)
        class FakeInteraction:
            def __init__(self, user_id, guild_id):
                self.user = type("obj", (object,), {"id": user_id})()
                self.guild = type("obj", (object,), {"id": guild_id})()

        fake_interaction = FakeInteraction(interaction.user.id, interaction.guild.id)
        embed = control_view.update_embed_and_buttons(fake_interaction, player)

        if embed:
            # 새 음악 메시지를 보내고 저장
            message = await interaction.followup.send(embed=embed, view=control_view)
            self.last_music_messages[interaction.guild.id] = message

    @app_commands.command(name="queue", description="Send music queue!")
    @app_commands.check(create_player)
    async def queue(self, interaction: discord.Interaction):
        await interaction.response.defer()

        try:
            player = self.bot.lavalink.player_manager.get(interaction.guild.id)
            if not player.queue:
                return await send_temp_embed(
                    interaction, interaction.guild.id, "music_no_music_in_the_playlist"
                )

            items_per_page = 10
            pages = [
                player.queue[i : i + items_per_page]
                for i in range(0, len(player.queue), items_per_page)
            ]

            class QueuePaginator(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=30)
                    self.current_page = 0
                    self.message = None

                async def on_timeout(self):
                    if self.message:
                        try:
                            await self.message.delete()
                        except:
                            pass

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
                            button_interaction.guild.id, "music_q"
                        ).format(lenQ=len(player.queue), queue_list=queue_list),
                        color=THEME_COLOR,
                    )
                    embed.set_footer(
                        text=f"{get_lan(button_interaction.guild.id, 'music_page')} {self.current_page + 1}/{len(pages)}\n{APP_NAME_TAG_VER}"
                    )
                    await button_interaction.response.edit_message(
                        embed=embed, view=self
                    )

            view = QueuePaginator()
            queue_list = ""
            for index, track in enumerate(pages[0], start=1):
                queue_list += f"`{index}.` [**{track.title}**]({track.uri})\n"
            embed = discord.Embed(
                description=get_lan(interaction.guild.id, "music_q").format(
                    lenQ=len(player.queue), queue_list=queue_list
                ),
                color=THEME_COLOR,
            )
            embed.set_footer(
                text=f"{get_lan(interaction.guild.id, 'music_page')} 1/{len(pages)}\n{APP_NAME_TAG_VER}"
            )
            message = await interaction.followup.send(embed=embed, view=view)
            view.message = message

        except Exception as e:
            error_embed = discord.Embed(
                title="Error",
                description=f"An error occurred while fetching the queue: {str(e)}",
                color=discord.Color.red(),
            )
            error_embed.set_footer(text=APP_NAME_TAG_VER)
            await send_temp_message(interaction, error_embed, delete_after=5)

    @app_commands.command(
        name="repeat", description="Repeat one song or repeat multiple songs!"
    )
    @app_commands.check(create_player)
    async def repeat(self, interaction: discord.Interaction):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        if not player.is_playing:
            return await send_temp_embed(
                interaction, interaction.guild.id, "music_not_playing"
            )

        if player.loop == 0:
            player.set_loop(1)
        elif player.loop == 1:
            player.set_loop(2)
        else:
            player.set_loop(0)

        Database().set_loop(interaction.guild.id, player.loop)

        if player.loop == 0:
            await send_temp_embed(interaction, interaction.guild.id, "music_repeat_off")
        elif player.loop == 1:
            await send_temp_embed(interaction, interaction.guild.id, "music_repeat_one")
        elif player.loop == 2:
            await send_temp_embed(interaction, interaction.guild.id, "music_repeat_all")

    @app_commands.command(name="remove", description="Remove music from the playlist!")
    @app_commands.describe(
        index="Queue에서 제거하고 싶은 음악이 몇 번째 음악인지 입력해 주세요"
    )
    @app_commands.check(create_player)
    async def remove(self, interaction: discord.Interaction, index: int):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        if not player.queue:
            return await send_temp_embed(
                interaction, interaction.guild.id, "music_remove_no_wating_music"
            )
        if index > len(player.queue) or index < 1:
            embed = discord.Embed(
                title=get_lan(interaction.guild.id, "music_remove_input_over").format(
                    last_queue=len(player.queue)
                ),
                color=THEME_COLOR,
            )
            embed.set_footer(text=APP_NAME_TAG_VER)
            return await send_temp_message(interaction, embed)
        removed = player.queue.pop(index - 1)
        embed = discord.Embed(
            title=get_lan(interaction.guild.id, "music_remove_form_playlist").format(
                remove_music=removed.title
            ),
            color=THEME_COLOR,
        )
        embed.set_footer(text=APP_NAME_TAG_VER)
        await send_temp_message(interaction, embed)

    @app_commands.command(
        name="shuffle",
        description="The music in the playlist comes out randomly from the next song!",
    )
    @app_commands.check(create_player)
    async def shuffle(self, interaction: discord.Interaction):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        if not player.is_playing:
            return await send_temp_embed(
                interaction, interaction.guild.id, "music_not_playing"
            )

        player.set_shuffle(not player.shuffle)
        Database().set_shuffle(interaction.guild.id, player.shuffle)

        if player.shuffle:
            await send_temp_embed(interaction, interaction.guild.id, "music_shuffle_on")
        else:
            await send_temp_embed(interaction, interaction.guild.id, "music_shuffle_off")

    @app_commands.command(name="clear", description="Clear the music queue")
    @app_commands.check(create_player)
    async def clear(self, interaction: discord.Interaction):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        if not player.queue:
            return await send_temp_embed(
                interaction, interaction.guild.id, "music_no_music_in_queue"
            )

        queue_length = len(player.queue)
        await self._cleanup_player(
            interaction.guild.id, stop_current=False, clear_queue=True
        )

        embed = discord.Embed(
            title=get_lan(interaction.guild.id, "music_queue_cleared"),
            description=get_lan(interaction.guild.id, "music_queue_cleared_desc").format(
                count=queue_length
            ),
            color=THEME_COLOR,
        )
        embed.set_footer(text=APP_NAME_TAG_VER)
        await send_temp_message(interaction, embed)

    @app_commands.command(name="volume", description="Changes or display the volume")
    @app_commands.describe(volume="볼륨값을 입력하세요")
    @app_commands.check(create_player)
    async def volume(self, interaction: discord.Interaction, volume: int = None):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        if volume is None:
            from tapi.utils import volumeicon

            volicon = volumeicon(player.volume)
            embed = discord.Embed(
                title=get_lan(interaction.guild.id, "music_now_vol").format(
                    volicon=volicon, volume=player.volume
                ),
                color=THEME_COLOR,
            )
            embed.set_footer(text=APP_NAME_TAG_VER)
            return await send_temp_message(interaction, embed)

        if volume > 100 or volume < 1:
            embed = discord.Embed(
                title=get_lan(interaction.guild.id, "music_input_over_vol"),
                description=get_lan(interaction.guild.id, "music_default_vol"),
                color=THEME_COLOR,
            )
            embed.set_footer(text=APP_NAME_TAG_VER)
            return await send_temp_message(interaction, embed)

        await player.set_volume(volume)
        Database().set_volume(interaction.guild.id, volume)

        from tapi.utils import volumeicon

        volicon = volumeicon(player.volume)
        embed = discord.Embed(
            title=get_lan(interaction.guild.id, "music_set_vol").format(
                volicon=volicon, volume=player.volume
            ),
            color=THEME_COLOR,
        )
        embed.set_footer(text=APP_NAME_TAG_VER)
        await send_temp_message(interaction, embed)

    @app_commands.command(name="pause", description="Pause or resume music!")
    @app_commands.check(create_player)
    async def pause(self, interaction: discord.Interaction):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        if not player.is_playing:
            return await send_temp_embed(
                interaction, interaction.guild.id, "music_not_playing"
            )
        if player.paused:
            await player.set_pause(False)
            await send_temp_embed(interaction, interaction.guild.id, "music_resume")
        else:
            await player.set_pause(True)
            await send_temp_embed(interaction, interaction.guild.id, "music_pause")


async def setup(bot):
    await bot.add_cog(Music(bot))
    LOGGER.info("Music loaded!")
