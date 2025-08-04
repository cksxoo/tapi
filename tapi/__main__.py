# tapi/__main__.py

import discord
import asyncio
import os
import time
import datetime
import psutil
from discord.ext import commands

import lavalink

from tapi import (
    LOGGER,
    TOKEN,
    EXTENSIONS,
    THEME_COLOR,
    APP_BANNER_URL,
    APP_NAME_TAG_VER,
    HOST,
    PORT,
    PSW,
)
from tapi.utils.language import get_lan
from tapi.utils.redis_manager import redis_manager


class TapiBot(commands.Bot):
    def __init__(self, shard_id=None, shard_count=None):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.guilds = True

        # 샤딩 설정
        if shard_id is not None and shard_count is not None:
            super().__init__(
                command_prefix="$",
                intents=intents,
                shard_id=shard_id,
                shard_count=shard_count,
            )
        else:
            super().__init__(command_prefix="$", intents=intents)

        self.remove_command("help")
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

        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening, name="📼 Cassette Tape"
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
                        type=discord.ActivityType.listening, name="📼 Cassette Tape"
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
                # 봇의 기본 언어 설정으로 환영 메시지 생성 (guild owner의 언어 설정 사용)
                try:
                    owner_id = guild.owner_id if guild.owner_id else self.user.id
                    title = get_lan(owner_id, "welcome_title")
                    description = get_lan(owner_id, "welcome_description")
                except:
                    # 언어 설정 실패 시 기본 영어 메시지 사용
                    title = "OMG! Hii guys ✧(≧◡≦) ♡"
                    description = "Thank you for inviting me to hang with yall (*≧▽≦)\n\nType /help to view my slash commands ♡"

                # 환영 메시지 embed 생성
                embed = discord.Embed(
                    title=title, description=description, color=0x7F8C8D
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

            # 활성 플레이어 수 계산
            player_count = 0
            if self.lavalink:
                for guild in self.guilds:
                    player = self.lavalink.player_manager.get(guild.id)
                    if player and player.is_connected:
                        player_count += 1

            # 레이턴시 계산
            latency = self.latency
            latency_ms = round(latency * 1000) if latency != float("inf") else -1

            shard_data = {
                "guild_count": len(self.guilds),
                "latency": latency_ms,
                "memory_usage": memory_info.rss,  # Resident Set Size in bytes
                "player_count": player_count,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
            redis_manager.update_shard_status(shard_id, shard_data)
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

    async def on_message(self, message):
        if message.author.bot:
            return
        await self.process_commands(message)


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

bot.run(TOKEN)
