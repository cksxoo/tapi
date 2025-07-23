import discord
import asyncio
import os
from discord.ext import commands

import lavalink

from musicbot import (
    LOGGER,
    TOKEN,
    EXTENSIONS,
    BOT_NAME_TAG_VER,
    HOST,
    PORT,
    PSW,
)


class MusicBot(commands.Bot):
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
                shard_count=shard_count
            )
            self.shard_info = f"Shard {shard_id}/{shard_count}"
        else:
            super().__init__(command_prefix="$", intents=intents)
            self.shard_info = "No Sharding"
            
        self.remove_command("help")

    async def setup_hook(self):
        self.lavalink = lavalink.Client(self.user.id)
        self.lavalink.add_node(HOST, PORT, PSW, 'eu', 'default-node')

        # 확장 기능 로드
        for extension in EXTENSIONS:
            await self.load_extension(f"musicbot.cogs.{extension}")

        # 슬래시 커맨드 동기화
        await self.tree.sync()
        LOGGER.info("Slash commands synced")

    async def on_ready(self):
        LOGGER.info(f"{BOT_NAME_TAG_VER} - {self.shard_info}")
        LOGGER.info(f"Connected to {len(self.guilds)} guilds on {self.shard_info}")
        
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening, 
                name=f"📼 {self.shard_info}"
            ),
            status=discord.Status.online,
        )
        self.loop.create_task(self.status_task())

    async def status_task(self):
        while True:
            try:
                await self.change_presence(
                    activity=discord.Activity(
                        type=discord.ActivityType.listening, name="📼 Cassette Tape"
                    ),
                    status=discord.Status.online,
                )
                await asyncio.sleep(10)
                await self.change_presence(
                    activity=discord.Activity(
                        type=discord.ActivityType.listening,
                        name=f"📼 {len(self.guilds)} servers",
                    ),
                    status=discord.Status.online,
                )
                await asyncio.sleep(10)
            except Exception:
                pass

    async def on_message(self, message):
        if message.author.bot:
            return
        await self.process_commands(message)


# 환경 변수에서 샤드 정보 가져오기
shard_id = os.getenv('SHARD_ID')
shard_count = os.getenv('SHARD_COUNT')

if shard_id is not None and shard_count is not None:
    shard_id = int(shard_id)
    shard_count = int(shard_count)
    LOGGER.info(f"Starting bot with shard {shard_id}/{shard_count}")
    bot = MusicBot(shard_id=shard_id, shard_count=shard_count)
else:
    LOGGER.info("Starting bot without sharding")
    bot = MusicBot()

bot.run(TOKEN)
