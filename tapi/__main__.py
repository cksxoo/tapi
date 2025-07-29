# tapi/__main__.py

import discord
import asyncio
import os
import time
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
)


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
            self.shard_info = f"Shard {shard_id}/{shard_count}"
        else:
            super().__init__(command_prefix="$", intents=intents)
            self.shard_info = "No Sharding"

        self.remove_command("help")
        self.lavalink = None  # ✅ lavalink 속성 미리 정의

    async def setup_hook(self):
        # Cog 로드
        for extension in EXTENSIONS:
            await self.load_extension(f"tapi.modules.{extension}")

        # shard 0일 때만 슬래시 동기화
        if getattr(self, "shard_id", None) == 0 or self.shard_info == "No Sharding":
            await self.tree.sync()
            LOGGER.info("Slash commands synced")
        else:
            LOGGER.info("Slash command sync skipped")

    async def on_ready(self):
        if self.lavalink is None:
            self.lavalink = lavalink.Client(self.user.id)
            self.lavalink.add_node(HOST, PORT, PSW, "eu", "default-node")
            LOGGER.info("Lavalink client initialized")

        LOGGER.info(f"{APP_NAME_TAG_VER} - {self.shard_info}")
        LOGGER.info(f"Connected to {len(self.guilds)} guilds on {self.shard_info}")

        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening, name=f"📼 {self.shard_info}"
            ),
            status=discord.Status.online,
        )

        self.loop.create_task(self.status_task())

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
