import re
import json
import time
import psutil
import discord
import requests
import lavalink
import platform
import datetime
import subprocess
from discord import app_commands
from discord.ext import commands

from musicbot.utils.language import get_lan
from musicbot import LOGGER, BOT_NAME_TAG_VER, COLOR_CODE


class Other(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="invite", description="Send you a link for invite me")
    async def invite(self, interaction: discord.Interaction):
        link = f"https://discord.com/api/oauth2/authorize?client_id={self.bot.user.id}&permissions=414501391424&scope=bot%20applications.commands"
        embed = discord.Embed(
            title=get_lan(interaction.user.id, "other_invite_title"),
            description=get_lan(interaction.user.id, "other_invite_description").format(
                link=link
            ),
            color=COLOR_CODE,
        )
        embed.set_footer(text=BOT_NAME_TAG_VER)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="softver", description="Let me tell you the version of the modules!"
    )
    async def softver(self, interaction: discord.Interaction):
        await interaction.response.defer()
        # 최신 discord.py 버전
        latest_discord_tag = json.loads(
            requests.get("https://api.github.com/repos/Rapptz/discord.py/releases").text
        )[0]["tag_name"]

        # 최신 lavalink.py 버전
        latest_lavalink_py_tag = json.loads(
            requests.get(
                "https://api.github.com/repos/Devoxin/Lavalink.py/releases"
            ).text
        )[0]["tag_name"]

        # 현재 자바 버전
        javaver = subprocess.check_output(
            ["java", "-version"], stderr=subprocess.STDOUT, encoding="utf-8"
        )
        now_javaver = re.search(r"version\s+\"(\d+.\d+.\d+)\"", javaver)
        now_javaver = now_javaver.group(1) if now_javaver else "None"

        # 현재 라바링크 버전
        lavalinkver = subprocess.check_output(
            ["java", "-jar", "Lavalink.jar", "--version"],
            stderr=subprocess.STDOUT,
            encoding="utf-8",
        )
        now_lavalinkver = re.search(r"Version:\s+(\d+\.\d+\.\d+)", lavalinkver)
        now_lavalinkver = now_lavalinkver.group(1) if now_lavalinkver else "None"

        # 최신 안정 라바링크 버전
        latest_lavalink_tag = ""
        lavalink_json = json.loads(
            requests.get(
                "https://api.github.com/repos/freyacodes/Lavalink/releases"
            ).text
        )
        for i in lavalink_json:
            if not i["prerelease"]:
                latest_lavalink_tag = i["tag_name"]
                break

        embed = discord.Embed(
            title=get_lan(interaction.user.id, "other_soft_ver"), color=COLOR_CODE
        )
        embed.add_field(
            name="Python Ver",
            value=f"{platform.python_implementation()} {platform.python_version()}",
            inline=False,
        )
        embed.add_field(
            name="discord.py Ver",
            value=f"{discord.__version__} (Latest: {latest_discord_tag})",
            inline=False,
        )
        embed.add_field(
            name="Lavalink.py Ver",
            value=f"{lavalink.__version__} (Latest: {latest_lavalink_py_tag})",
            inline=False,
        )
        embed.add_field(name="Java Ver", value=now_javaver, inline=False)
        embed.add_field(
            name="Lavalink Ver",
            value=f"{now_lavalinkver} (Latest: {latest_lavalink_tag})",
            inline=False,
        )
        embed.set_footer(text=BOT_NAME_TAG_VER)
        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="uptime", description="Let me tell you the server's uptime!"
    )
    async def uptime(self, interaction: discord.Interaction):
        uptime_string = str(
            datetime.timedelta(seconds=int(time.time() - psutil.boot_time()))
        )
        embed = discord.Embed(
            title=get_lan(interaction.user.id, "other_uptime"),
            description=f"```{uptime_string}```",
            color=COLOR_CODE,
        )
        embed.set_footer(text=BOT_NAME_TAG_VER)
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Other(bot))
    LOGGER.info("Other loaded!")
