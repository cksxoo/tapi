import discord
from discord import app_commands
from discord.ext import commands

from tapi.utils.language import get_lan
from tapi import LOGGER, APP_NAME_TAG_VER, THEME_COLOR
from tapi.modules.player import send_temp_message


class Other(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="invite", description="Send you a link for invite me")
    async def invite(self, interaction: discord.Interaction):
        link = f"https://discord.com/oauth2/authorize?client_id={self.bot.user.id}&permissions=414501391424&scope=bot"
        embed = discord.Embed(
            title=get_lan(interaction.user.id, "other_invite_title"),
            description=get_lan(interaction.user.id, "other_invite_description").format(
                link=link
            ),
            color=THEME_COLOR,
        )
        embed.set_footer(text=APP_NAME_TAG_VER)
        await interaction.response.defer()
        await send_temp_message(interaction, embed, delete_after=8)



async def setup(bot):
    await bot.add_cog(Other(bot))
    LOGGER.info("Other loaded!")
