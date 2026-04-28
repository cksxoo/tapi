import discord
import asyncio
import os
import signal
import time
import datetime
from datetime import timezone, timedelta
import psutil
from discord.ext import commands

import lavalink

from tapi import (
    LOGGER,
    TOKEN,
    EXTENSIONS,
    APP_NAME_TAG_VER,
    HOST,
    PORT,
    PSW,
    CLIENT_ID,
    TOPGG_TOKEN,
    KOREANBOT_TOKEN,
    MESSAGE_CONTENT_INTENT,
)
from tapi.utils.redis_manager import redis_manager
from tapi.utils.stats_updater import BotStatsUpdater
from tapi.utils.embed import get_track_thumbnail
from tapi.modules.audio_connection import AudioConnection
from discord import ui
from tapi import SUCCESS_COLOR, WARNING_COLOR
from tapi.utils.v2_components import (
    make_themed_container,
    make_separator,
    make_banner_gallery,
)


class TapiBot(commands.Bot):
    def __init__(self, shard_id=None, shard_count=None):
        intents = discord.Intents.none()
        intents.guilds = True  # For basic guild operations
        intents.voice_states = True  # For Lavalink to manage voice channels
        intents.messages = (
            MESSAGE_CONTENT_INTENT  # For on_message event (bot channel auto-play)
        )
        intents.message_content = MESSAGE_CONTENT_INTENT  # config 플래그로 조절

        # 샤딩 설정
        if shard_id is not None and shard_count is not None:
            super().__init__(
                command_prefix=lambda bot, msg: [],
                intents=intents,
                shard_id=shard_id,
                shard_count=shard_count,
            )
        else:
            super().__init__(command_prefix=lambda bot, msg: [], intents=intents)

        self.lavalink = None  # ✅ lavalink 속성 미리 정의
        self.stats_updater = None  # 봇 통계 업데이터

    async def setup_hook(self):
        # Cog 로드
        for extension in EXTENSIONS:
            await self.load_extension(f"tapi.modules.{extension}")

        # 전역 인터랙션 체크 등록 (봇 전용 채널 제한)
        self.tree.interaction_check = self._global_interaction_check

        # shard 0일 때만 슬래시 동기화
        if getattr(self, "shard_id", None) == 0 or not hasattr(self, "shard_id"):
            await self.tree.sync()
            LOGGER.info("Slash commands synced")
        else:
            LOGGER.info("Slash command sync skipped")

    async def _global_interaction_check(self, interaction: discord.Interaction) -> bool:
        """전역 인터랙션 체크: 봇 전용 채널이 설정된 경우 해당 채널에서만 명령어 허용"""
        # DM은 그대로 허용
        if interaction.guild is None:
            return True

        # /setting 명령어는 채널 제한 없이 허용 (채널 설정 변경을 위해 필요)
        if interaction.command and interaction.command.name == "setting":
            return True

        # DB에서 봇 전용 채널 조회
        from tapi.utils.database import Database

        bot_channel_id = Database().get_channel(interaction.guild.id)

        if bot_channel_id and interaction.channel_id != bot_channel_id:
            bot_channel = interaction.guild.get_channel(bot_channel_id)
            channel_mention = (
                bot_channel.mention if bot_channel else f"<#{bot_channel_id}>"
            )
            from tapi.utils.language import get_lan

            await interaction.response.send_message(
                get_lan(interaction, "channel_restrict_message").format(
                    channel=channel_mention
                ),
                ephemeral=True,
            )
            return False

        return True

    async def on_ready(self):
        if self.lavalink is None:
            self.lavalink = lavalink.Client(self.user.id)
            self.lavalink.add_node(HOST, PORT, PSW, "eu", "default-node")
            LOGGER.info("Lavalink client initialized")

        # 통계 업데이터 초기화 (config의 CLIENT_ID 사용)
        if self.stats_updater is None:
            self.stats_updater = BotStatsUpdater(
                bot_id=CLIENT_ID,
                topgg_token=TOPGG_TOKEN,
                koreanbot_token=KOREANBOT_TOKEN,
            )
            LOGGER.info(f"Bot stats updater initialized for bot ID: {CLIENT_ID}")

        shard_info = (
            f"Shard {getattr(self, 'shard_id', 'N/A')}/{getattr(self, 'shard_count', 'N/A')}"
            if hasattr(self, "shard_id")
            else "No Sharding"
        )
        LOGGER.info(f"{APP_NAME_TAG_VER} - {shard_info}")
        LOGGER.info(f"Connected to {len(self.guilds)} guilds on {shard_info}")
        LOGGER.info(
            f"Bot intents: guilds={self.intents.guilds}, voice_states={self.intents.voice_states}"
        )

        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening, name="🎶 ヾ(｡>﹏<｡)ﾉﾞ✧"
            ),
            status=discord.Status.online,
        )

        # Redis 연결 및 샤드 정보 업데이트
        redis_manager.connect()
        await self.update_shard_status()

        self.loop.create_task(self.status_task())
        self.loop.create_task(self.redis_update_task())
        self.loop.create_task(self.voice_cleanup_task())

        # 웹 대시보드 명령 리스너 시작
        from tapi.utils.redis_command_listener import start_command_listener

        self.loop.create_task(start_command_listener(self))

        # 점검 후 재생 상태 복원 (잠시 대기 후 실행)
        self.loop.create_task(self._delayed_restore_playback())

        # shard 0만 봇 통계 업데이트 및 업타임 모니터링 담당
        if getattr(self, "shard_id", 0) == 0 or not hasattr(self, "shard_id"):
            self.loop.create_task(self.stats_update_task())
            self.loop.create_task(self.uptime_check_task())
            LOGGER.info("Bot stats update & uptime check tasks started")

    async def status_task(self):
        await self.wait_until_ready()

        status_messages = [
            "Vacation Vibes 🌴",
            "Seaside Tunes ⛱️",
            "Ocean Breeze 🌊",
        ]

        index = 0
        while True:
            try:
                status = status_messages[index]
                index = (index + 1) % len(status_messages)
                await self.change_presence(
                    activity=discord.Activity(
                        type=discord.ActivityType.listening,
                        name=status,
                    ),
                    status=discord.Status.online,
                )
                await asyncio.sleep(15)
            except Exception as e:
                LOGGER.error(f"Error in status_task: {e}")
                await asyncio.sleep(30)

    async def on_guild_join(self, guild):
        """봇이 새로운 서버에 초대되었을 때 환영 메시지 전송"""
        try:
            # 서버에서 봇이 메시지를 보낼 수 있는 첫 번째 채널 찾기
            channel = None

            # 일반 채널 중에서 찾기
            for ch in guild.text_channels:
                if ch.permissions_for(guild.me).send_messages:
                    channel = ch
                    break

            # 시스템 채널이 있다면 우선 사용
            if (
                guild.system_channel
                and guild.system_channel.permissions_for(guild.me).send_messages
            ):
                channel = guild.system_channel

            if channel:
                # 환영 메시지 V2 레이아웃
                welcome_view = ui.LayoutView(timeout=None)
                welcome_view.add_item(
                    make_themed_container(
                        ui.TextDisplay("## Thanks for adding TAPI!"),
                        ui.TextDisplay("Use `/help` to see available commands."),
                        make_separator(),
                        make_banner_gallery(),
                        accent_color=SUCCESS_COLOR,
                    )
                )

                await channel.send(view=welcome_view)
                LOGGER.info(
                    f"Welcome message sent to guild: {guild.name} (ID: {guild.id})"
                )
            else:
                LOGGER.warning(
                    f"Could not find a suitable channel to send welcome message in guild: {guild.name} (ID: {guild.id})"
                )

        except Exception as e:
            LOGGER.error(f"Error sending welcome message to guild {guild.name}: {e}")

    async def update_shard_status(self):
        """현재 샤드의 상태 정보를 Redis에 업데이트"""
        try:
            shard_id = getattr(self, "shard_id", 0)

            # 메모리 사용량 정보 가져오기
            process = psutil.Process()
            memory_info = process.memory_info()

            # 활성 플레이어 수 계산 및 상세 정보 수집
            player_count = 0
            active_players = []

            if self.lavalink:
                for guild in self.guilds:
                    player = self.lavalink.player_manager.get(guild.id)
                    if player and player.is_connected:
                        player_count += 1

                        # 활성 플레이어 상세 정보 수집
                        voice_client = guild.voice_client
                        channel_name = "Unknown"
                        channel_id = None
                        user_count = 0

                        if voice_client and voice_client.channel:
                            channel_name = voice_client.channel.name
                            channel_id = voice_client.channel.id
                            user_count = len(voice_client.channel.members) - 1  # 봇 제외

                        # 현재 재생 중인 트랙 정보
                        current_track = None
                        if player.current:
                            current_track = {
                                "title": player.current.title,
                                "author": player.current.author,
                                "uri": player.current.uri,
                                "duration": player.current.duration,
                                "position": player.position,
                                "thumbnail": get_track_thumbnail(player.current),
                            }

                        # 큐 상세 정보
                        queue = []
                        for track in player.queue:
                            queue.append(
                                {
                                    "title": track.title,
                                    "author": track.author,
                                    "uri": track.uri,
                                    "duration": track.duration,
                                    "thumbnail": get_track_thumbnail(track),
                                }
                            )

                        active_players.append(
                            {
                                "guild_id": str(guild.id),
                                "guild_name": guild.name,
                                "channel_id": str(channel_id) if channel_id else None,
                                "channel_name": channel_name,
                                "user_count": user_count,
                                "is_connected": True,
                                "is_playing": player.is_playing,
                                "is_paused": player.paused,
                                "current_track": current_track,
                                "queue": queue,
                                "queue_length": len(player.queue),
                                "volume": player.volume,
                                "loop": player.loop,
                                "shuffle": player.shuffle,
                            }
                        )

            # 레이턴시 계산
            latency = self.latency
            latency_ms = round(latency * 1000) if latency != float("inf") else -1

            shard_data = {
                "guild_count": len(self.guilds),
                "latency": latency_ms,
                "memory_usage": memory_info.rss,  # Resident Set Size in bytes
                "player_count": player_count,
                "timestamp": datetime.datetime.now(timezone(timedelta(hours=9)))
                .replace(microsecond=0)
                .isoformat(),
            }
            redis_manager.update_shard_status(shard_id, shard_data)

            # 활성 플레이어 상세 정보도 Redis에 업데이트
            redis_manager.update_active_players(shard_id, active_players)

            # 봇이 속한 길드 ID 목록 업데이트
            guild_ids = [str(g.id) for g in self.guilds]
            redis_manager.update_bot_guilds(shard_id, guild_ids)

            LOGGER.debug(f"Updated shard {shard_id} status: {shard_data}")
        except Exception as e:
            LOGGER.error(f"Error updating shard status: {e}")

    async def redis_update_task(self):
        """Redis 상태 업데이트 주기적 작업"""
        await self.wait_until_ready()

        while True:
            try:
                await self.update_shard_status()
                await asyncio.sleep(15)  # 15초마다 업데이트
            except Exception as e:
                LOGGER.error(f"Error in redis_update_task: {e}")
                await asyncio.sleep(60)

    async def voice_cleanup_task(self):
        """빈 음성 채널에 잔류한 봇을 주기적으로 정리 (이벤트 드롭/강제 이동 대비 안전망)"""
        await self.wait_until_ready()
        await asyncio.sleep(60)  # 부팅/복원 로직 완료 대기

        while True:
            try:
                music_cog = self.get_cog("Music")
                handlers = getattr(music_cog, "handlers", None) if music_cog else None

                for guild in list(self.guilds):
                    try:
                        voice_client = guild.voice_client
                        if not voice_client or not voice_client.channel:
                            continue

                        player = self.lavalink.player_manager.get(guild.id)
                        is_active = bool(
                            player and (player.is_playing or player.paused)
                        )

                        non_bot_members = [
                            m for m in voice_client.channel.members if not m.bot
                        ]

                        # 잔류 조건: 유저가 없거나, 플레이어가 활성 상태가 아님
                        if non_bot_members and is_active:
                            continue

                        LOGGER.info(
                            f"[voice_cleanup] Cleaning up guild {guild.id} "
                            f"(users={len(non_bot_members)}, active={is_active})"
                        )

                        if handlers:
                            await handlers._full_disconnect_cleanup(
                                guild.id, "health_check"
                            )
                        else:
                            # Music cog 로딩 전이라면 voice_client만이라도 정리
                            await voice_client.disconnect(force=True)
                    except Exception as e:
                        LOGGER.error(
                            f"Error in voice_cleanup for guild {guild.id}: {e}"
                        )

                await asyncio.sleep(120)
            except Exception as e:
                LOGGER.error(f"Error in voice_cleanup_task: {e}")
                await asyncio.sleep(120)

    async def stats_update_task(self):
        """봇 리스팅 사이트 통계 업데이트 주기적 작업 (shard 0만 실행)"""
        await self.wait_until_ready()

        # 첫 업데이트까지 잠시 대기 (모든 샤드가 준비될 시간 확보)
        await asyncio.sleep(30)

        while True:
            try:
                # 샤딩 사용 시 모든 샤드의 길드 수 합산
                if hasattr(self, "shard_count") and self.shard_count:
                    # Redis에서 모든 샤드의 길드 수 한 번에 가져오기
                    all_shards = redis_manager.get_all_shard_statuses()
                    total_guilds = sum(
                        shard_data.get("guild_count", 0)
                        for shard_data in all_shards.values()
                    )
                    shard_count = self.shard_count
                else:
                    # 샤딩 미사용 시 현재 봇의 길드 수
                    total_guilds = len(self.guilds)
                    shard_count = None

                # 봇 리스팅 사이트 업데이트
                if self.stats_updater and total_guilds > 0:
                    await self.stats_updater.update_all(total_guilds, shard_count)
                    LOGGER.info(f"📊 Bot stats updated: {total_guilds} guilds")

                # 6시간마다 업데이트
                await asyncio.sleep(21600)

            except Exception as e:
                LOGGER.error(f"Error in stats_update_task: {e}")
                await asyncio.sleep(600)  # 에러 발생 시 10분 대기

    async def uptime_check_task(self):
        """업타임 모니터링 태스크 (shard 0만, 5분 간격)"""
        await self.wait_until_ready()
        await asyncio.sleep(60)  # 초기 대기

        import aiohttp

        KST = timezone(timedelta(hours=9))
        SERVICES = ["shard_0", "shard_1", "bot", "lavalink", "web", "api"]
        LAVALINK_URL = f"http://{HOST}:{PORT}/v4/info"
        LAVALINK_HEADERS = {"Authorization": PSW}
        WEB_URL = os.getenv("WEB_URL", "http://tapi-web:3000/")
        API_URL = "https://vote-worker.cksxoo.workers.dev/"

        while True:
            try:
                now = datetime.datetime.now(KST)
                date_str = now.strftime("%Y-%m-%d")
                check_index = (now.hour * 60 + now.minute) // 5  # 0-287

                # 샤드 상태 체크 (Redis 타임스탬프 45초 이내)
                shard_statuses = redis_manager.get_all_shard_statuses()
                shard_up = {}
                for sid in range(getattr(self, "shard_count", 1)):
                    shard_data = shard_statuses.get(sid)
                    if shard_data and shard_data.get("timestamp"):
                        ts = datetime.datetime.fromisoformat(shard_data["timestamp"])
                        shard_up[sid] = (now - ts).total_seconds() < 45
                    else:
                        shard_up[sid] = False

                results = {
                    "shard_0": shard_up.get(0, False),
                    "shard_1": shard_up.get(1, False),
                    "bot": any(shard_up.values()),
                }

                # Lavalink 체크
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            LAVALINK_URL, headers=LAVALINK_HEADERS, timeout=aiohttp.ClientTimeout(total=5)
                        ) as resp:
                            results["lavalink"] = resp.status == 200
                except Exception:
                    results["lavalink"] = False

                # Web 체크
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            WEB_URL, timeout=aiohttp.ClientTimeout(total=5)
                        ) as resp:
                            results["web"] = resp.status == 200
                except Exception:
                    results["web"] = False

                # API (vote-worker) 체크
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            API_URL, timeout=aiohttp.ClientTimeout(total=5)
                        ) as resp:
                            results["api"] = resp.status == 200
                except Exception:
                    results["api"] = False

                # Redis 비트맵에 기록
                for service in SERVICES:
                    is_up = results.get(service, False)
                    redis_manager.record_uptime_check(service, date_str, check_index, is_up)

                LOGGER.debug(f"Uptime check recorded: {results}")

                # 전날 집계 시도
                yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
                if not redis_manager.is_uptime_aggregated(yesterday):
                    from tapi.utils.database import Database
                    db = Database()
                    all_success = True
                    inserted_count = 0
                    for service in SERVICES:
                        summary = redis_manager.get_uptime_summary(service, yesterday)
                        if summary["total_checks"] > 0:
                            success = db.insert_uptime_history(
                                service, yesterday,
                                summary["total_checks"], summary["up_checks"]
                            )
                            if success:
                                inserted_count += 1
                            else:
                                all_success = False
                    if all_success and inserted_count > 0:
                        redis_manager.mark_uptime_aggregated(yesterday)
                        LOGGER.info(f"Uptime aggregated for {yesterday}: {inserted_count} services")
                    elif inserted_count == 0:
                        LOGGER.warning(f"No uptime data to aggregate for {yesterday}")
                    else:
                        LOGGER.error(f"Uptime aggregation partially failed for {yesterday}: {inserted_count} succeeded, not marking as done")

            except Exception as e:
                LOGGER.error(f"Error in uptime_check_task: {e}")

            await asyncio.sleep(300)  # 5분

    async def close(self):
        """봇 종료 시 자동 공지 - 각 샤드가 자기 활성 플레이어에게 직접 전송"""
        if not getattr(self, "_closing", False):
            self._closing = True

            shard_id = getattr(self, "shard_id", 0)
            LOGGER.info(
                f"Shard {shard_id} shutting down, sending announcements to active players..."
            )

            # 재생 상태 저장 (점검 후 복원용)
            await self._save_playback_states()

            # 현재 샤드의 활성 플레이어에게 직접 전송
            if self.lavalink:
                sent_count = 0
                for guild in self.guilds:
                    player = self.lavalink.player_manager.get(guild.id)

                    if player and player.is_connected:
                        channel_id = player.fetch("channel")
                        if channel_id:
                            channel = self.get_channel(channel_id)
                            if channel:
                                try:
                                    shutdown_view = ui.LayoutView(timeout=None)
                                    shutdown_view.add_item(
                                        make_themed_container(
                                            ui.TextDisplay(
                                                "**<:reset:1448850253234311250> Bot Restarting**"
                                            ),
                                            ui.TextDisplay(
                                                "The bot is restarting for maintenance.\n"
                                                "If you stay in the voice channel, playback will resume automatically."
                                            ),
                                            make_separator(),
                                            make_banner_gallery(),
                                            accent_color=WARNING_COLOR,
                                        )
                                    )
                                    await channel.send(view=shutdown_view)
                                    sent_count += 1
                                except Exception as e:
                                    LOGGER.warning(
                                        f"Failed to send shutdown notice to {guild.name}: {e}"
                                    )

                LOGGER.info(
                    f"Shard {shard_id} sent shutdown announcement to {sent_count} channels"
                )
                await asyncio.sleep(2)  # 메시지 전송 완료 대기

                # 음악 컨트롤 메시지 정리
                music_cog = self.get_cog("Music")
                if music_cog and hasattr(music_cog, "last_music_messages"):
                    deleted_count = 0
                    for guild_id, message in list(
                        music_cog.last_music_messages.items()
                    ):
                        try:
                            await message.delete()
                            deleted_count += 1
                        except Exception as e:
                            LOGGER.debug(
                                f"Error deleting music message for guild {guild_id}: {e}"
                            )
                    music_cog.last_music_messages.clear()
                    LOGGER.info(
                        f"Shard {shard_id} deleted {deleted_count} music control messages"
                    )

            # stats_updater 세션 종료
            if self.stats_updater:
                await self.stats_updater.close()

        await super().close()

    async def _save_playback_states(self):
        """점검 전 활성 플레이어의 재생 상태를 Redis에 저장"""
        if not self.lavalink:
            return

        shard_id = getattr(self, "shard_id", 0)
        playback_states = []

        for guild in self.guilds:
            try:
                player = self.lavalink.player_manager.get(guild.id)
                if not player or not player.is_connected:
                    continue

                # 현재 재생 중이거나 큐에 곡이 있는 경우만 저장
                if not player.current and not player.queue:
                    continue

                voice_client = guild.voice_client
                if not voice_client or not voice_client.channel:
                    continue

                # 현재 트랙 정보
                current_track = None
                if player.current:
                    current_track = {
                        "uri": player.current.uri,
                        "title": player.current.title,
                        "author": player.current.author,
                        "requester": player.current.requester,
                    }

                # 큐 정보 (최대 50곡)
                queue_data = []
                for i, track in enumerate(player.queue):
                    if i >= 50:
                        break
                    queue_data.append(
                        {
                            "uri": track.uri,
                            "title": track.title,
                            "author": track.author,
                            "requester": track.requester,
                        }
                    )

                state = {
                    "guild_id": guild.id,
                    "voice_channel_id": voice_client.channel.id,
                    "text_channel_id": player.fetch("channel"),
                    "current_track": current_track,
                    "queue": queue_data,
                    "volume": player.volume,
                    "loop": player.loop,
                    "shuffle": player.shuffle,
                }
                playback_states.append(state)

            except Exception as e:
                LOGGER.error(f"Error saving playback state for guild {guild.id}: {e}")

        if playback_states:
            redis_manager.save_playback_state(shard_id, playback_states)
            LOGGER.info(
                f"Saved {len(playback_states)} playback states for shard {shard_id}"
            )

    async def _delayed_restore_playback(self):
        """Lavalink 노드 준비 후 재생 상태 복원"""
        await self.wait_until_ready()

        # Lavalink 노드가 준비될 시간을 줌
        await asyncio.sleep(5)

        # Lavalink 노드 연결 확인
        if not self.lavalink or not self.lavalink.node_manager.available_nodes:
            LOGGER.warning("No available Lavalink nodes, skipping playback restore")
            return

        await self.restore_playback_states()

    async def restore_playback_states(self):
        """점검 후 조건부 자동 재생 복원"""
        shard_id = getattr(self, "shard_id", 0)
        states = redis_manager.get_playback_states(shard_id)

        if not states:
            LOGGER.debug(f"No playback states to restore for shard {shard_id}")
            return

        LOGGER.info(
            f"Attempting to restore {len(states)} playback states for shard {shard_id}"
        )
        restored_count = 0

        for state in states:
            try:
                guild = self.get_guild(state["guild_id"])
                if not guild:
                    LOGGER.debug(
                        f"Guild {state['guild_id']} not found, skipping restore"
                    )
                    continue

                # 음성 채널 확인
                voice_channel = guild.get_channel(state["voice_channel_id"])
                if not voice_channel:
                    LOGGER.debug(
                        f"Voice channel {state['voice_channel_id']} not found in guild {guild.id}"
                    )
                    continue

                # 조건 확인: 음성 채널에 사용자가 있는지
                non_bot_members = [m for m in voice_channel.members if not m.bot]
                if len(non_bot_members) == 0:
                    LOGGER.debug(
                        f"No users in voice channel {voice_channel.id}, skipping restore for guild {guild.id}"
                    )
                    continue

                # 자동 재생 복원
                success = await self._restore_player(guild, state)
                if success:
                    restored_count += 1

            except Exception as e:
                LOGGER.error(
                    f"Error restoring playback for guild {state.get('guild_id')}: {e}"
                )

        # 복원 완료 후 Redis에서 상태 삭제
        redis_manager.clear_playback_state(shard_id)
        LOGGER.info(
            f"Restored {restored_count}/{len(states)} playback states for shard {shard_id}"
        )

    async def _restore_player(self, guild, state):
        """개별 플레이어 상태 복원"""
        try:
            voice_channel = guild.get_channel(state["voice_channel_id"])
            text_channel = guild.get_channel(state["text_channel_id"])

            if not voice_channel:
                return False

            # 권한 확인
            permissions = voice_channel.permissions_for(guild.me)
            if not permissions.connect or not permissions.speak:
                LOGGER.warning(f"Missing voice permissions in guild {guild.id}")
                return False

            # 음성 채널 연결
            try:
                await voice_channel.connect(cls=AudioConnection, self_deaf=True)
            except Exception as e:
                LOGGER.error(
                    f"Failed to connect to voice channel in guild {guild.id}: {e}"
                )
                return False

            # 플레이어 가져오기
            player = self.lavalink.player_manager.get(guild.id)
            if not player:
                LOGGER.error(f"Player not created for guild {guild.id}")
                return False

            # 설정 복원
            player.store("channel", state["text_channel_id"])
            await player.set_volume(state.get("volume", 20))
            player.set_loop(state.get("loop", 0))
            player.set_shuffle(state.get("shuffle", False))

            tracks_added = 0

            # 현재 곡 복원
            if state.get("current_track"):
                try:
                    results = await player.node.get_tracks(
                        state["current_track"]["uri"]
                    )
                    if results and results.tracks:
                        track = results.tracks[0]
                        track.requester = state["current_track"].get(
                            "requester", self.user.id
                        )
                        player.add(track=track, requester=track.requester)
                        tracks_added += 1
                except Exception as e:
                    LOGGER.warning(f"Failed to restore current track: {e}")

            # 큐 복원
            for track_data in state.get("queue", []):
                try:
                    results = await player.node.get_tracks(track_data["uri"])
                    if results and results.tracks:
                        track = results.tracks[0]
                        track.requester = track_data.get("requester", self.user.id)
                        player.add(track=track, requester=track.requester)
                        tracks_added += 1
                except Exception as e:
                    LOGGER.warning(f"Failed to restore queued track: {e}")

            # 재생 시작
            if tracks_added > 0 and not player.is_playing:
                await player.play()

            # 복원 알림
            if text_channel and tracks_added > 0:
                try:
                    restore_view = ui.LayoutView(timeout=None)
                    restore_view.add_item(
                        make_themed_container(
                            ui.TextDisplay(
                                "**<:reset:1448850253234311250> Playback Resumed**"
                            ),
                            ui.TextDisplay(
                                f"Music playback has been automatically restored after maintenance.\n**{tracks_added}** track(s) restored."
                            ),
                            make_separator(),
                            make_banner_gallery(),
                            accent_color=SUCCESS_COLOR,
                        )
                    )
                    await text_channel.send(view=restore_view)
                except Exception as e:
                    LOGGER.warning(f"Failed to send restore notification: {e}")

            LOGGER.info(
                f"Restored playback for guild {guild.id} with {tracks_added} tracks"
            )
            return tracks_added > 0

        except Exception as e:
            LOGGER.error(f"Failed to restore player for guild {guild.id}: {e}")
            return False


# ────── 실행부 ──────
shard_id = os.getenv("SHARD_ID")
shard_count = os.getenv("SHARD_COUNT")

if shard_id is not None and shard_count is not None:
    shard_id = int(shard_id)
    shard_count = int(shard_count)
    LOGGER.info(f"Starting bot with shard {shard_id}/{shard_count}")

    IDENTIFY_DELAY = 5
    time.sleep(shard_id * IDENTIFY_DELAY)

    bot = TapiBot(shard_id=shard_id, shard_count=shard_count)
else:
    LOGGER.info("Starting bot without sharding")
    bot = TapiBot()


# Signal handler 설정 (Linux/Docker 환경)
def handle_shutdown(signum, frame):
    """SIGTERM/SIGINT 받았을 때 graceful shutdown"""
    _ = frame  # unused parameter
    LOGGER.info(f"Received signal {signum}, initiating graceful shutdown...")
    asyncio.create_task(bot.close())


# Docker에서는 Linux이므로 항상 등록
signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)
LOGGER.info("Signal handlers registered for graceful shutdown")

bot.run(TOKEN)
