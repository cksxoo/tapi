import discord
from discord import app_commands
from discord.ext import commands

from tapi.utils.language import get_lan
from tapi import LOGGER, THEME_COLOR, APP_BANNER_URL
from tapi.utils.embed import send_temp_message


class Other(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="invite", description="Send you a link for invite me")
    async def invite(self, interaction: discord.Interaction):
        link = f"https://discord.com/oauth2/authorize?client_id={self.bot.user.id}&permissions=414501391424&scope=bot"
        embed = discord.Embed(
            title=get_lan(interaction, "other_invite_title"),
            description=get_lan(interaction, "other_invite_description").format(
                link=link
            ),
            color=THEME_COLOR,
        )
        embed.set_image(url=APP_BANNER_URL)
        await interaction.response.defer()
        await send_temp_message(interaction, embed, delete_after=8)


async def setup(bot):
    await bot.add_cog(Other(bot))
    LOGGER.info("Other loaded!")
