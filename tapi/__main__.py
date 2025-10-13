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
    APP_BANNER_URL,
    APP_NAME_TAG_VER,
    HOST,
    PORT,
    PSW,
)
from tapi.utils.redis_manager import redis_manager


class TapiBot(commands.Bot):
    def __init__(self, shard_id=None, shard_count=None):
        intents = discord.Intents.none()
        intents.guilds = True  # For basic guild operations
        intents.voice_states = True  # For Lavalink to manage voice channels

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

    async def setup_hook(self):
        # Cog 로드
        for extension in EXTENSIONS:
            await self.load_extension(f"tapi.modules.{extension}")

        # shard 0일 때만 슬래시 동기화
        if getattr(self, "shard_id", None) == 0 or not hasattr(self, "shard_id"):
            await self.tree.sync()
            LOGGER.info("Slash commands synced")
        else:
            LOGGER.info("Slash command sync skipped")

    async def on_ready(self):
        if self.lavalink is None:
            self.lavalink = lavalink.Client(self.user.id)
            self.lavalink.add_node(HOST, PORT, PSW, "eu", "default-node")
            LOGGER.info("Lavalink client initialized")

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
                type=discord.ActivityType.listening, name="🎶 music! ヾ(｡>﹏<｡)ﾉﾞ✧"
            ),
            status=discord.Status.online,
        )

        # Redis 연결 및 샤드 정보 업데이트
        redis_manager.connect()
        await self.update_shard_status()

        self.loop.create_task(self.status_task())
        self.loop.create_task(self.redis_update_task())

    async def status_task(self):
        await self.wait_until_ready()

        while True:
            try:
                await self.change_presence(
                    activity=discord.Activity(
                        type=discord.ActivityType.listening,
                        name="🎶 music! ヾ(｡>﹏<｡)ﾉﾞ✧",
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
                # 환영 메시지 embed 생성 (영어 하드코딩)
                embed = discord.Embed(
                    title="OMG! Hii guys ✧(≧◡≦) ♡",
                    description="Thank you for inviting me to hang with yall (*≧▽≦)\n\nType /help to view my slash commands ♡",
                    color=0x7F8C8D,
                )
                embed.set_image(url=APP_BANNER_URL)

                await channel.send(embed=embed)
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
                            user_count = (
                                len(voice_client.channel.members) - 1
                            )  # 봇 제외

                        # 현재 재생 중인 트랙 정보
                        current_track = None
                        if player.current:
                            current_track = {
                                "title": player.current.title,
                                "author": player.current.author,
                                "uri": player.current.uri,
                                "duration": player.current.duration,
                                "position": player.position,
                            }

                        active_players.append(
                            {
                                "guild_id": guild.id,
                                "guild_name": guild.name,
                                "channel_id": channel_id,
                                "channel_name": channel_name,
                                "user_count": user_count,
                                "is_playing": player.is_playing,
                                "is_paused": player.paused,
                                "current_track": current_track,
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

    async def close(self):
        """봇 종료 시 자동 공지 - 각 샤드가 자기 활성 플레이어에게 직접 전송"""
        if not getattr(self, '_closing', False):
            self._closing = True

            shard_id = getattr(self, 'shard_id', 0)
            LOGGER.info(f"Shard {shard_id} shutting down, sending announcements to active players...")

            # 현재 샤드의 활성 플레이어에게 직접 전송
            if self.lavalink:
                sent_count = 0
                for guild in self.guilds:
                    player = self.lavalink.player_manager.get(guild.id)

                    if player and player.is_connected:
                        channel_id = player.fetch('channel')
                        if channel_id:
                            channel = self.get_channel(channel_id)
                            if channel:
                                try:
                                    embed = discord.Embed(
                                        title="🔄 Bot Restarting",
                                        description="The bot is restarting for maintenance. Music playback will resume shortly.",
                                        color=0x3b82f6
                                    )
                                    embed.set_footer(text=APP_NAME_TAG_VER)
                                    await channel.send(embed=embed)
                                    sent_count += 1
                                except Exception as e:
                                    LOGGER.warning(f"Failed to send shutdown notice to {guild.name}: {e}")

                LOGGER.info(f"Shard {shard_id} sent shutdown announcement to {sent_count} channels")
                await asyncio.sleep(2)  # 메시지 전송 완료 대기

        await super().close()


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
