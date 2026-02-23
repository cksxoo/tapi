import re
import traceback

import discord
from discord import app_commands, ui
from discord.ext import commands

import lavalink
from lavalink.server import LoadType

from tapi.utils.language import get_lan
from tapi import (
    LOGGER,
    THEME_COLOR,
    WARNING_COLOR,
    APP_NAME_TAG_VER,
    APP_BANNER_URL,
    HOST,
    PSW,
    REGION,
    PORT,
)
from tapi.utils.database import Database
from tapi.utils.statistics import Statistics
from tapi.utils.v2_components import (
    make_themed_container, make_separator,
    send_temp_v2, send_temp_status,
    create_track_layout, create_playlist_layout, create_error_layout,
    StatusLayout,
)

# 분리된 모듈들 import
from tapi.modules.audio_connection import AudioConnection
from tapi.modules.music_views import SearchLayout, MusicControlLayout, QueuePaginatorLayout
from tapi.modules.music_handlers import MusicHandlers

url_rx = re.compile(r"https?://(?:www\.)?.+")

MAX_QUEUE_SIZE = 50
MAX_PLAYLIST_TRACKS = 20


# 투표 확인 데코레이터
async def check_vote(interaction: discord.Interaction):
    """사용자가 투표했는지 확인"""
    db = Database()
    if not db.has_voted(interaction.user.id):
        # 유저 locale 감지 (ko, en, ja 지원)
        user_locale = str(interaction.locale)
        if user_locale.startswith("ko"):
            lang = "ko"
        elif user_locale.startswith("ja"):
            lang = "ja"
        else:
            lang = "en"

        # 언어 파일에서 메시지 가져오기
        import json

        try:
            with open(f"tapi/languages/{lang}.json", encoding="utf-8") as f:
                language_data = json.load(f)
            title = language_data.get("vote_required_title", "🗳️ Vote Required!")
            description = language_data.get(
                "vote_required_description",
                "To use TAPI, please vote for us first.\nJust vote once and you can use it forever!",
            )
        except:
            title = "🗳️ Vote Required!"
            description = "To use TAPI, please vote for us first.\nJust vote once and you can use it forever!"

        # V2 투표 요청 레이아웃
        layout = ui.LayoutView(timeout=None)
        layout.add_item(make_themed_container(
            ui.TextDisplay(f"**{title}**"),
            ui.TextDisplay(f"{interaction.user.mention} {description}"),
            make_separator(),
            ui.ActionRow(
                ui.Button(
                    emoji="<:koreanbots:1422912074819960833>",
                    label="KoreanBots Vote",
                    url="https://koreanbots.dev/bots/1157593204682657933/vote",
                    style=discord.ButtonStyle.link,
                ),
                ui.Button(
                    emoji="<:topgg:1422912056549441630>",
                    label="Top.gg Vote",
                    url="https://top.gg/bot/1157593204682657933/vote",
                    style=discord.ButtonStyle.link,
                ),
            ),
            accent_color=WARNING_COLOR,
        ))

        await interaction.response.send_message(view=layout, ephemeral=True)
        return False
    return True


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 길드별 마지막 음악 메시지를 저장하는 딕셔너리
        self.last_music_messages = {}
        # 사용자별 언어 설정 캐시
        self.user_locales = {}  # {user_id: locale}
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

    async def _publish_web_state(self, guild_id: int, command: str):
        """웹 대시보드에 상태 변경 전파"""
        try:
            from tapi.utils.redis_manager import redis_manager
            from tapi.utils.web_command_handler import get_player_state
            if redis_manager.available:
                state = get_player_state(self.bot, guild_id)
                await redis_manager.publish_player_update(guild_id, command, state)
        except Exception:
            pass

    # 핸들러 메서드들을 위임
    async def _cleanup_music_message(self, guild_id: int, reason: str = "cleanup"):
        return await self.handlers._cleanup_music_message(guild_id, reason)

    async def _cleanup_player(
        self, guild_id: int, stop_current: bool = True, clear_queue: bool = True
    ):
        return await self.handlers._cleanup_player(guild_id, stop_current, clear_queue)

    async def _full_disconnect_cleanup(
        self,
        guild_id: int,
        reason: str = "disconnect",
    ):
        return await self.handlers._full_disconnect_cleanup(guild_id, reason)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        return await self.handlers.on_voice_state_update(member, before, after)

    @staticmethod
    async def _setup_player_settings(player, guild_id: int):
        """플레이어 설정 초기화"""
        db = Database()
        settings = db.get_guild_settings(guild_id)

        # 볼륨 설정
        saved_volume = settings.get("volume", 20)
        await player.set_volume(saved_volume)

        # 반복 상태 설정
        loop = settings.get("loop_mode", 0)
        if loop is not None:
            player.set_loop(loop)

        # 셔플 상태 설정
        shuffle = settings.get("shuffle", False)
        if shuffle is not None:
            player.set_shuffle(shuffle)

    @staticmethod
    async def _validate_user_voice_state(interaction: discord.Interaction):
        """사용자 음성 상태 검증"""
        if not interaction.user.voice or not interaction.user.voice.channel:
            # Check 함수 내에서는 interaction을 소비하지 않도록 예외만 발생
            raise app_commands.CheckFailure("User not in voice channel")

        return interaction.user.voice.channel

    @staticmethod
    async def _validate_voice_permissions(
        interaction: discord.Interaction, voice_channel
    ):
        """음성 채널 권한 검증"""
        permissions = voice_channel.permissions_for(interaction.guild.me)

        if not permissions.connect or not permissions.speak:
            text = get_lan(interaction, "music_no_permission")
            layout = StatusLayout(title_text=text, style="error")
            await interaction.response.send_message(view=layout, ephemeral=True)
            raise app_commands.CheckFailure(
                get_lan(interaction, "music_no_permission")
            )

        if voice_channel.user_limit > 0:
            if (
                len(voice_channel.members) >= voice_channel.user_limit
                and not interaction.guild.me.guild_permissions.move_members
            ):
                raise app_commands.CheckFailure(
                    get_lan(interaction, "music_voice_channel_is_full")
                )

    def _save_user_locale(self, interaction: discord.Interaction):
        """사용자의 언어 설정을 캐시에 저장"""
        if hasattr(interaction, 'locale'):
            self.user_locales[interaction.user.id] = str(interaction.locale)

    @staticmethod
    async def create_player(interaction: discord.Interaction):
        """
        A check that is invoked before any commands marked with `@app_commands.check(create_player)` can run.

        This function will try to create a player for the guild associated with this Interaction, or raise
        an error which will be relayed to the user if one cannot be created.
        """
        if interaction.guild is None:
            raise app_commands.NoPrivateMessage()

        # Check if Lavalink is initialized
        if interaction.client.lavalink is None:
            raise app_commands.CheckFailure(
                "Music system is still initializing. Please try again in a few seconds."
            )

        try:
            existing = interaction.client.lavalink.player_manager.get(
                interaction.guild.id
            )
            player = interaction.client.lavalink.player_manager.create(
                interaction.guild.id
            )
            # 새로 생성된 플레이어만 DB 설정 적용 (기존 플레이어 볼륨 덮어쓰기 방지)
            if existing is None:
                await Music._setup_player_settings(player, interaction.guild.id)
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
            "spplay",
            "search",
            "connect",
            "load",
        )

        voice_client = interaction.guild.voice_client
        voice_channel = await Music._validate_user_voice_state(interaction)

        if voice_client is None:
            if not should_connect:
                raise app_commands.CheckFailure(
                    get_lan(interaction, "music_not_connected_voice_channel")
                )

            await Music._validate_voice_permissions(interaction, voice_channel)
            player.store("channel", interaction.channel.id)
            await voice_channel.connect(cls=AudioConnection)
        elif voice_client.channel.id != voice_channel.id:
            raise app_commands.CheckFailure(
                get_lan(interaction, "music_come_in_my_voice_channel")
            )

        return True

    @staticmethod
    async def require_playing(interaction: discord.Interaction):
        if interaction.guild is None:
            raise app_commands.NoPrivateMessage()

        # Check if user is in a voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            # Check 함수 내에서는 interaction을 소비하지 않도록 예외만 발생
            raise app_commands.CheckFailure("User not in voice channel")

        # Get player
        player = interaction.client.lavalink.player_manager.get(interaction.guild.id)

        # Check if music is playing
        if not player.is_playing:
            # Check 함수 내에서는 interaction을 소비하지 않도록 예외만 발생
            raise app_commands.CheckFailure("Music not playing")

        return True

    @app_commands.command(name="connect", description="Connect to voice channel!")
    @app_commands.check(create_player)
    async def connect(self, interaction: discord.Interaction):
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        if not player.is_connected:
            text = get_lan(interaction, "music_connect_voice_channel")
        else:
            text = get_lan(interaction, "music_already_connected_voice_channel")

        layout = StatusLayout(title_text=text, style="info")
        await interaction.response.send_message(view=layout)

    def _prepare_query(self, query: str) -> tuple[str, bool]:
        """쿼리를 처리하고 검색 타입을 결정"""
        original_query_stripped = query.strip("<>")
        is_search_query = not url_rx.match(original_query_stripped)

        if is_search_query:
            return f"ytsearch:{original_query_stripped}", is_search_query

        # YouTube 검색결과 페이지 URL → 검색어로 변환
        yt_search_match = re.match(
            r"https?://(?:www\.)?youtube\.com/results\?search_query=([^&]+)",
            original_query_stripped,
        )
        if yt_search_match:
            from urllib.parse import unquote
            search_term = unquote(yt_search_match.group(1))
            return f"ytsearch:{search_term}", True

        # URL인 경우 처리
        if (
            "youtube.com" in original_query_stripped
            or "youtu.be" in original_query_stripped
        ):
            # YouTube URL: 동적 재생목록 파라미터만 제거
            # 라디오/믹스 등 동적 재생목록만 제거 (RD, RDMM 등)
            # 일반 재생목록 (PL, UU 등)은 유지
            current_lavalink_query = re.sub(
                r"[&?]list=RD[^&]*", "", original_query_stripped
            )
            # index 파라미터는 제거 (재생목록의 특정 곡 순서)
            current_lavalink_query = re.sub(
                r"[&?]index=[^&]*", "", current_lavalink_query
            )
            # start_radio 파라미터 제거
            current_lavalink_query = re.sub(
                r"[&?]start_radio=[^&]*", "", current_lavalink_query
            )
            current_lavalink_query = re.sub(
                r"[&?]+",
                lambda m: (
                    "?" if m.start() == original_query_stripped.find("?") else "&"
                ),
                current_lavalink_query,
            )
            return current_lavalink_query.rstrip("&?"), is_search_query

        # Spotify, SoundCloud 등 다른 URL은 그대로 Lavalink에 전달
        # Lavalink의 LavaSrc 플러그인이 자동으로 처리함
        return original_query_stripped, is_search_query

    async def _search_tracks(
        self, player, query: str, original_query: str, is_search_query: bool
    ):
        """트랙 검색 처리"""
        current_query = query
        nofind = 0

        while True:
            results = await player.node.get_tracks(current_query)

            if results.load_type == LoadType.EMPTY or not results or not results.tracks:
                nofind += 1
                if nofind >= 3:
                    return None
            else:
                return results

    def _create_track_layout(self, results, interaction: discord.Interaction):
        """트랙 또는 플레이리스트에 대한 V2 레이아웃 생성"""
        if results.load_type == LoadType.PLAYLIST:
            return create_playlist_layout(
                interaction, results.playlist_info.name, len(results.tracks)
            )
        else:
            track = results.tracks[0]
            return create_track_layout(track, interaction.user.display_name)

    def _get_queue_size(self, player):
        """현재 큐 크기 (재생 중인 곡 포함)"""
        return len(player.queue) + (1 if player.current else 0)

    async def _add_tracks_to_player(self, player, results, user_id: int):
        """플레이어에 트랙 추가 (큐 제한 적용). 추가된 곡 수와 총 곡 수를 반환."""
        current_size = self._get_queue_size(player)
        remaining = MAX_QUEUE_SIZE - current_size

        if results.load_type == LoadType.PLAYLIST:
            added = 0
            for track in results.tracks:
                if added >= remaining:
                    break
                try:
                    player.add(requester=user_id, track=track)
                    added += 1
                except Exception as e:
                    LOGGER.error(f"Error adding track from playlist: {e}")
            return added, len(results.tracks)
        else:
            if remaining <= 0:
                return 0, 1
            track = results.tracks[0]
            player.add(requester=user_id, track=track)
            return 1, 1

    @app_commands.command(
        name="play", description="Searches and plays a song from a given query."
    )
    @app_commands.describe(query="찾고싶은 음악의 제목이나 링크를 입력하세요")
    @app_commands.check(create_player)
    async def play(self, interaction: discord.Interaction, query: str):
        # 투표 확인
        if not await check_vote(interaction):
            return

        # 사용자 언어 설정 저장
        self._save_user_locale(interaction)

        await interaction.response.defer()

        try:
            player = self.bot.lavalink.player_manager.get(interaction.guild.id)
            original_query_stripped = query.strip("<>")

            # 쿼리 준비
            current_lavalink_query, is_search_query = self._prepare_query(query)

            # 트랙 검색
            results = await self._search_tracks(
                player, current_lavalink_query, original_query_stripped, is_search_query
            )

            if not results:
                layout = create_error_layout(
                    f"{get_lan(interaction, 'music_can_not_find_anything')}\nQuery: {original_query_stripped}"
                )
                return await send_temp_v2(interaction, layout)

            # 큐 제한 체크
            if self._get_queue_size(player) >= MAX_QUEUE_SIZE:
                text = get_lan(interaction, "music_queue_full").format(max=MAX_QUEUE_SIZE)
                layout = StatusLayout(title_text=text, style="error")
                return await send_temp_v2(interaction, layout)

            # 플레이어에 트랙 추가
            added, total = await self._add_tracks_to_player(player, results, interaction.user.id)

            # V2 레이아웃 생성 및 전송
            layout = self._create_track_layout(results, interaction)
            await send_temp_v2(interaction, layout)

            # 플레이리스트에서 일부만 추가된 경우 알림
            if added < total:
                partial_text = get_lan(interaction, "music_queue_full_partial").format(
                    added=added, total=total, max=MAX_QUEUE_SIZE
                )
                partial_layout = StatusLayout(title_text=partial_text, style="warning")
                await interaction.followup.send(view=partial_layout, ephemeral=True)

            if not player.is_playing:
                await player.play()
            else:
                # 이미 재생 중이면 큐만 변경 → 웹 대시보드에 상태 전파
                try:
                    from tapi.utils.redis_manager import redis_manager
                    from tapi.utils.web_command_handler import get_player_state
                    if redis_manager.available:
                        state = get_player_state(self.bot, interaction.guild.id)
                        await redis_manager.publish_player_update(
                            interaction.guild.id, "queue_add", state
                        )
                except Exception:
                    pass

        except Exception as e:
            LOGGER.error(f"Error in play command: {e}")
            try:
                Statistics().record_play(
                    track=(
                        results.tracks[0]
                        if "results" in locals() and results and results.tracks
                        else None
                    ),
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
        # 투표 확인
        if not await check_vote(interaction):
            return

        # 사용자 언어 설정 저장
        self._save_user_locale(interaction)

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
                    layout = create_error_layout(
                        get_lan(interaction.guild.id, "music_can_not_find_anything")
                    )
                    return await send_temp_v2(interaction, layout)
            else:
                break

        # 큐 제한 체크
        if self._get_queue_size(player) >= MAX_QUEUE_SIZE:
            text = get_lan(interaction, "music_queue_full").format(max=MAX_QUEUE_SIZE)
            layout = StatusLayout(title_text=text, style="error")
            return await send_temp_v2(interaction, layout)

        added, total = await self._add_tracks_to_player(player, results, interaction.user.id)

        layout = self._create_track_layout(results, interaction)
        await send_temp_v2(interaction, layout)

        if added < total:
            partial_text = get_lan(interaction, "music_queue_full_partial").format(
                added=added, total=total, max=MAX_QUEUE_SIZE
            )
            partial_layout = StatusLayout(title_text=partial_text, style="warning")
            await interaction.followup.send(view=partial_layout, ephemeral=True)

        if not player.is_playing:
            await player.play()
        else:
            try:
                from tapi.utils.redis_manager import redis_manager
                from tapi.utils.web_command_handler import get_player_state
                if redis_manager.available:
                    state = get_player_state(self.bot, interaction.guild.id)
                    await redis_manager.publish_player_update(
                        interaction.guild.id, "queue_add", state
                    )
            except Exception:
                pass

    @app_commands.command(
        name="spplay", description="Searches and plays a song from Spotify."
    )
    @app_commands.describe(
        query="Spotify에서 찾고싶은 음악의 제목이나 링크를 입력하세요"
    )
    @app_commands.check(create_player)
    async def spplay(self, interaction: discord.Interaction, query: str):
        # 투표 확인
        if not await check_vote(interaction):
            return

        # 사용자 언어 설정 저장
        self._save_user_locale(interaction)

        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        query = query.strip("<>")

        if not url_rx.match(query):
            query = f"spsearch:{query}"

        nofind = 0
        while True:
            results = await player.node.get_tracks(query)

            if results.load_type == LoadType.EMPTY or not results or not results.tracks:
                if nofind < 3:
                    nofind += 1
                elif nofind == 3:
                    layout = create_error_layout(
                        get_lan(interaction.guild.id, "music_can_not_find_anything")
                    )
                    return await send_temp_v2(interaction, layout)
            else:
                break

        # 큐 제한 체크
        if self._get_queue_size(player) >= MAX_QUEUE_SIZE:
            text = get_lan(interaction, "music_queue_full").format(max=MAX_QUEUE_SIZE)
            layout = StatusLayout(title_text=text, style="error")
            return await send_temp_v2(interaction, layout)

        added, total = await self._add_tracks_to_player(player, results, interaction.user.id)

        layout = self._create_track_layout(results, interaction)
        await send_temp_v2(interaction, layout)

        if added < total:
            partial_text = get_lan(interaction, "music_queue_full_partial").format(
                added=added, total=total, max=MAX_QUEUE_SIZE
            )
            partial_layout = StatusLayout(title_text=partial_text, style="warning")
            await interaction.followup.send(view=partial_layout, ephemeral=True)

        if not player.is_playing:
            await player.play()
        else:
            try:
                from tapi.utils.redis_manager import redis_manager
                from tapi.utils.web_command_handler import get_player_state
                if redis_manager.available:
                    state = get_player_state(self.bot, interaction.guild.id)
                    await redis_manager.publish_player_update(
                        interaction.guild.id, "queue_add", state
                    )
            except Exception:
                pass

    @app_commands.command(
        name="search", description="Search for songs with a given keyword"
    )
    @app_commands.describe(query="Enter the keyword to search for songs")
    @app_commands.check(create_player)
    async def search(self, interaction: discord.Interaction, query: str):
        # 투표 확인
        if not await check_vote(interaction):
            return

        # 사용자 언어 설정 저장
        self._save_user_locale(interaction)

        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        if not query:
            return await send_temp_status(interaction, "music_search_no_keyword", style="error")

        query = f"ytsearch:{query}"
        results = await player.node.get_tracks(query)

        if not results or not results.tracks:
            return await send_temp_status(interaction, "music_search_no_results", style="error")

        tracks = results.tracks[:5]

        view = SearchLayout(tracks, self, interaction)
        message = await interaction.followup.send(view=view)
        view.message = message

    async def play_search_result(self, interaction: discord.Interaction, track):
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        if self._get_queue_size(player) >= MAX_QUEUE_SIZE:
            text = get_lan(interaction, "music_queue_full").format(max=MAX_QUEUE_SIZE)
            layout = StatusLayout(title_text=text, style="error")
            return await send_temp_v2(interaction, layout)

        player.add(requester=interaction.user.id, track=track)

        layout = create_track_layout(track, interaction.user.display_name)
        await send_temp_v2(interaction, layout)

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
            return await send_temp_status(
                interaction, "music_dc_not_connect_voice_channel", style="error"
            )

        if not interaction.user.voice or (
            player.is_connected
            and interaction.user.voice.channel.id != int(player.channel_id)
        ):
            text = get_lan(interaction.guild.id, "music_dc_not_connect_my_voice_channel").format(
                name=interaction.user.name
            )
            layout = StatusLayout(title_text=text, style="error")
            return await send_temp_v2(interaction, layout)

        guild_id = interaction.guild.id
        await self._full_disconnect_cleanup(
            guild_id,
            "manual_disconnect",
        )

        await send_temp_status(interaction, "music_dc_disconnected", style="info")

    @app_commands.command(name="skip", description="Skip to the next song!")
    @app_commands.check(require_playing)
    async def skip(self, interaction: discord.Interaction):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        # 한 곡 반복모드일 때는 전체 반복으로 전환 후 skip
        if player.loop == 1:  # 한 곡 반복모드
            player.set_loop(2)  # 전체 반복으로 전환
            Database().set_loop(interaction.guild.id, 2)  # 설정 저장

        await player.skip()
        await send_temp_status(interaction, "music_skip_next", style="music")

    @app_commands.command(
        name="nowplaying", description="Sending the currently playing song!"
    )
    @app_commands.check(require_playing)
    async def nowplaying(self, interaction: discord.Interaction):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        # 기존 음악 메시지 삭제
        await self._cleanup_music_message(interaction.guild.id, "nowplaying_command")

        # 새로운 V2 컨트롤 패널 생성
        control_layout = MusicControlLayout(self, interaction.guild.id)
        control_layout.build_layout(interaction, player)

        # 새 음악 메시지를 보내고 저장
        message = await interaction.followup.send(view=control_layout)
        self.last_music_messages[interaction.guild.id] = message

    @app_commands.command(name="queue", description="Send music queue!")
    @app_commands.check(create_player)
    async def queue(self, interaction: discord.Interaction):
        await interaction.response.defer()

        try:
            player = self.bot.lavalink.player_manager.get(interaction.guild.id)
            if not player.queue:
                return await send_temp_status(
                    interaction, "music_no_music_in_the_playlist", style="error"
                )

            items_per_page = 10
            pages = [
                player.queue[i : i + items_per_page]
                for i in range(0, len(player.queue), items_per_page)
            ]

            view = QueuePaginatorLayout(interaction, player, pages)
            message = await interaction.followup.send(view=view)
            view.message = message

        except Exception as e:
            layout = create_error_layout(
                f"An error occurred while fetching the queue: {str(e)}"
            )
            await send_temp_v2(interaction, layout, delete_after=5)

    @app_commands.command(
        name="repeat", description="Repeat one song or repeat multiple songs!"
    )
    @app_commands.check(require_playing)
    async def repeat(self, interaction: discord.Interaction):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        if player.loop == 0:
            player.set_loop(1)
        elif player.loop == 1:
            player.set_loop(2)
        else:
            player.set_loop(0)

        Database().set_loop(interaction.guild.id, player.loop)

        if player.loop == 0:
            await send_temp_status(interaction, "music_repeat_off", style="music")
        elif player.loop == 1:
            await send_temp_status(interaction, "music_repeat_one", style="music")
        elif player.loop == 2:
            await send_temp_status(interaction, "music_repeat_all", style="music")
        await self._publish_web_state(interaction.guild.id, "repeat")

    @app_commands.command(name="remove", description="Remove music from the playlist!")
    @app_commands.describe(
        index="Queue에서 제거하고 싶은 음악이 몇 번째 음악인지 입력해 주세요"
    )
    @app_commands.check(create_player)
    async def remove(self, interaction: discord.Interaction, index: int):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        if not player.queue:
            return await send_temp_status(
                interaction, "music_remove_no_wating_music", style="error"
            )
        if index > len(player.queue) or index < 1:
            text = get_lan(interaction, "music_remove_input_over").format(
                last_queue=len(player.queue)
            )
            layout = StatusLayout(title_text=text, style="error")
            return await send_temp_v2(interaction, layout)
        removed = player.queue.pop(index - 1)
        text = get_lan(interaction, "music_remove_form_playlist").format(
            remove_music=removed.title
        )
        layout = StatusLayout(title_text=text, style="success")
        await send_temp_v2(interaction, layout)
        await self._publish_web_state(interaction.guild.id, "remove")

    @app_commands.command(
        name="shuffle",
        description="The music in the playlist comes out randomly from the next song!",
    )
    @app_commands.check(require_playing)
    async def shuffle(self, interaction: discord.Interaction):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        player.set_shuffle(not player.shuffle)
        Database().set_shuffle(interaction.guild.id, player.shuffle)

        if player.shuffle:
            await send_temp_status(interaction, "music_shuffle_on", style="music")
        else:
            await send_temp_status(interaction, "music_shuffle_off", style="music")
        await self._publish_web_state(interaction.guild.id, "shuffle")

    @app_commands.command(name="clear", description="Clear the music queue")
    @app_commands.check(create_player)
    async def clear(self, interaction: discord.Interaction):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        if not player.queue:
            return await send_temp_status(interaction, "music_no_music_in_queue", style="error")

        queue_length = len(player.queue)
        await self._cleanup_player(
            interaction.guild.id, stop_current=False, clear_queue=True
        )

        title = get_lan(interaction, "music_queue_cleared")
        desc = get_lan(interaction, "music_queue_cleared_desc").format(count=queue_length)
        layout = StatusLayout(title_text=title, description_text=desc, style="success")
        await send_temp_v2(interaction, layout)
        await self._publish_web_state(interaction.guild.id, "clear")

    @app_commands.command(name="volume", description="Changes or display the volume")
    @app_commands.describe(volume="볼륨값을 입력하세요")
    @app_commands.check(require_playing)
    async def volume(self, interaction: discord.Interaction, volume: int = None):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        if volume is None:
            from tapi.utils import volumeicon
            volicon = volumeicon(player.volume)
            text = get_lan(interaction, "music_now_vol").format(
                volicon=volicon, volume=player.volume
            )
            layout = StatusLayout(title_text=text, style="info")
            return await send_temp_v2(interaction, layout)

        if volume > 100 or volume < 1:
            title = get_lan(interaction, "music_input_over_vol")
            desc = get_lan(interaction, "music_default_vol")
            layout = StatusLayout(title_text=title, description_text=desc, style="error")
            return await send_temp_v2(interaction, layout)

        await player.set_volume(volume)
        Database().set_volume(interaction.guild.id, volume)

        from tapi.utils import volumeicon
        volicon = volumeicon(player.volume)
        text = get_lan(interaction, "music_set_vol").format(
            volicon=volicon, volume=player.volume
        )
        layout = StatusLayout(title_text=text, style="info")
        await send_temp_v2(interaction, layout)
        await self._publish_web_state(interaction.guild.id, "volume")

    @app_commands.command(name="pause", description="Pause or resume music!")
    @app_commands.check(require_playing)
    async def pause(self, interaction: discord.Interaction):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        if player.paused:
            await player.set_pause(False)
            await send_temp_status(interaction, "music_resume", style="music")
        else:
            await player.set_pause(True)
            await send_temp_status(interaction, "music_pause", style="music")
        await self._publish_web_state(interaction.guild.id, "pause")

    # ===== 플레이리스트 커맨드 =====

    @app_commands.command(name="save", description="Save current queue as your playlist")
    @app_commands.check(require_playing)
    async def save(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        tracks_data = []
        if player.current:
            tracks_data.append({
                "title": player.current.title,
                "author": player.current.author,
                "uri": player.current.uri,
                "duration": player.current.duration,
                "identifier": player.current.identifier,
                "source_name": player.current.source_name,
            })

        total_tracks = 1 + len(player.queue) if player.current else len(player.queue)
        truncated = total_tracks > MAX_PLAYLIST_TRACKS

        for track in player.queue:
            if len(tracks_data) >= MAX_PLAYLIST_TRACKS:
                break
            tracks_data.append({
                "title": track.title,
                "author": track.author,
                "uri": track.uri,
                "duration": track.duration,
                "identifier": track.identifier,
                "source_name": track.source_name,
            })

        if not tracks_data:
            return await send_temp_status(interaction, "playlist_save_empty", style="error")

        db = Database()
        result = db.save_playlist(interaction.user.id, tracks_data)

        if not result:
            text = get_lan(interaction, "playlist_save_error")
            layout = StatusLayout(title_text=text, style="error")
            return await interaction.followup.send(view=layout, ephemeral=True)

        title = get_lan(interaction, "playlist_saved")
        desc = get_lan(interaction, "playlist_saved_desc").format(count=len(tracks_data))
        if truncated:
            desc += "\n" + get_lan(interaction, "playlist_save_truncated").format(
                max=MAX_PLAYLIST_TRACKS
            )
        layout = StatusLayout(title_text=title, description_text=desc, style="success")
        await interaction.followup.send(view=layout, ephemeral=True)

    @app_commands.command(name="load", description="Load your saved playlist into the queue")
    @app_commands.check(create_player)
    async def load(self, interaction: discord.Interaction):
        if not await check_vote(interaction):
            return

        self._save_user_locale(interaction)
        await interaction.response.defer()

        db = Database()
        playlist = db.load_playlist(interaction.user.id)

        if not playlist:
            text = get_lan(interaction, "playlist_not_found")
            layout = StatusLayout(title_text=text, style="error")
            return await send_temp_v2(interaction, layout)

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        tracks_data = playlist.get("tracks", [])

        if not tracks_data:
            text = get_lan(interaction, "playlist_empty")
            layout = StatusLayout(title_text=text, style="error")
            return await send_temp_v2(interaction, layout)

        # 기존 큐 비우고 현재 곡 정지
        player.queue.clear()
        await player.stop()

        loading_text = get_lan(interaction, "playlist_loading").format(
            count=len(tracks_data)
        )
        loading_layout = StatusLayout(title_text=loading_text, style="info")
        loading_msg = await interaction.followup.send(view=loading_layout)

        loaded_count = 0
        failed_count = 0

        for track_data in tracks_data:
            try:
                uri = track_data.get("uri")
                if not uri:
                    failed_count += 1
                    continue

                results = await player.node.get_tracks(uri)

                if results and results.tracks:
                    player.add(requester=interaction.user.id, track=results.tracks[0])
                    loaded_count += 1
                else:
                    search_query = f"ytsearch:{track_data.get('title', '')} {track_data.get('author', '')}"
                    results = await player.node.get_tracks(search_query)
                    if results and results.tracks:
                        player.add(requester=interaction.user.id, track=results.tracks[0])
                        loaded_count += 1
                    else:
                        failed_count += 1
            except Exception as e:
                LOGGER.error(f"Error resolving track: {e}")
                failed_count += 1

        try:
            await loading_msg.delete()
        except Exception:
            pass

        if loaded_count > 0:
            # 첫 번째 트랙 재생 시작
            if not player.is_playing:
                await player.play()
            title = get_lan(interaction, "playlist_loaded")
            desc = get_lan(interaction, "playlist_loaded_desc").format(count=loaded_count)
            if failed_count > 0:
                desc += "\n" + get_lan(interaction, "playlist_load_failed_some").format(
                    count=failed_count
                )
            layout = StatusLayout(title_text=title, description_text=desc, style="success")
        else:
            title = get_lan(interaction, "playlist_load_failed")
            layout = StatusLayout(title_text=title, style="error")

        await send_temp_v2(interaction, layout, delete_after=5)

        if not player.is_playing and loaded_count > 0:
            await player.play()
        elif loaded_count > 0:
            await self._publish_web_state(interaction.guild.id, "queue_add")

    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        """Cog 레벨 에러 핸들러"""
        if isinstance(error, app_commands.CheckFailure):
            # CheckFailure인 경우, 사용자에게 친절한 메시지 전송
            error_message = str(error)
            
            if "User not in voice channel" in error_message:
                text = get_lan(interaction, "music_not_in_voice_channel_description")
            elif "Music not playing" in error_message:
                text = get_lan(interaction, "music_not_playing")
            else:
                # 다른 CheckFailure는 로그만 남김
                LOGGER.warning(f"CheckFailure: {error}")
                return

            error_layout = StatusLayout(title_text=text, style="error")

            # interaction이 이미 응답되지 않았다면 응답
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(view=error_layout, ephemeral=True)
                else:
                    await interaction.followup.send(view=error_layout, ephemeral=True)
            except Exception as e:
                LOGGER.error(f"Failed to send error message: {e}")
        else:
            # 다른 에러는 기본 처리
            LOGGER.error(f"Command error in {interaction.command.name}: {error}")


async def setup(bot):
    await bot.add_cog(Music(bot))
    LOGGER.info("Music loaded!")
