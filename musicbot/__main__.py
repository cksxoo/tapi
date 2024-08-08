import time
import discord
import asyncio
import multiprocessing
from discord.ext import commands
from musicbot.lavalinkstart import start_lavalink, download_lavalink
import lavalink

from musicbot import (
    LOGGER,
    TOKEN,
    EXTENSIONS,
    BOT_NAME_TAG_VER,
    LAVALINK_AUTO_UPDATE,
)

class MusicBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.guilds = True
        super().__init__(command_prefix="$", intents=intents)
        self.remove_command("help")

        if LAVALINK_AUTO_UPDATE:
            download_lavalink()

        LOGGER.info("Lavalink starting...")
        self.lavalink_process = multiprocessing.Process(target=start_lavalink)
        self.lavalink_process.start()
        time.sleep(20)
        LOGGER.info("Lavalink process started")

    async def setup_hook(self):        
        # 확장 기능 로드
        for extension in EXTENSIONS:
            await self.load_extension(f"musicbot.cogs.{extension}")

        # 슬래시 커맨드 동기화
        await self.tree.sync()
        LOGGER.info("Slash commands synced")

    async def on_ready(self):
        LOGGER.info(BOT_NAME_TAG_VER)
        await self.change_presence(
            activity=discord.Game("/help : 도움말"),
            status=discord.Status.online,
        )
        self.loop.create_task(self.status_task())

    async def status_task(self):
        while True:
            try:
                await self.change_presence(
                    activity=discord.Game("/help : 도움말"),
                    status=discord.Status.online,
                )
                await asyncio.sleep(10)
                await self.change_presence(
                    activity=discord.Game(f"{len(self.guilds)}개의 서버에서 놀고있어요!"),
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