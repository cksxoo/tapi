import discord
import asyncio
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
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.guilds = True
        super().__init__(command_prefix="$", intents=intents)
        self.remove_command("help")

    async def setup_hook(self):
        self.lavalink = lavalink.Client(self.user.id)
        self.lavalink.add_node(HOST, PORT, PSW, 'eu', 'default-node', ws_path='/v4/websocket')

        # 확장 기능 로드
        for extension in EXTENSIONS:
            await self.load_extension(f"musicbot.cogs.{extension}")

        # 슬래시 커맨드 동기화
        await self.tree.sync()
        LOGGER.info("Slash commands synced")

    async def on_ready(self):
        LOGGER.info(BOT_NAME_TAG_VER)
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening, name="📼 Cassette Tape"
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


bot = MusicBot()
bot.run(TOKEN)
