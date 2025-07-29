import time
import psutil
import discord
import datetime
from discord import app_commands
from discord.ext import commands

from tapi.utils.language import get_lan
from tapi import LOGGER, APP_NAME_TAG_VER, THEME_COLOR


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
            color=THEME_COLOR,
        )
        embed.set_footer(text=APP_NAME_TAG_VER)
        await interaction.response.send_message(embed=embed)

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
            color=THEME_COLOR,
        )
        embed.set_footer(text=APP_NAME_TAG_VER)
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Other(bot))
    LOGGER.info("Other loaded!")
