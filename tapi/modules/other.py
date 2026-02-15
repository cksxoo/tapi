import discord
from discord import app_commands, ui
from discord.ext import commands

from tapi.utils.language import get_lan
from tapi import LOGGER, THEME_COLOR, APP_BANNER_URL, APP_NAME_TAG_VER
from tapi.utils.v2_components import (
    make_themed_container, make_banner_gallery, make_separator, send_temp_v2,
)


class Other(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="invite", description="Send you a link for invite me")
    async def invite(self, interaction: discord.Interaction):
        link = f"https://discord.com/oauth2/authorize?client_id={self.bot.user.id}&permissions=414501391424&scope=bot"
        title = get_lan(interaction, "other_invite_title")
        desc = get_lan(interaction, "other_invite_description").format(link=link)

        layout = ui.LayoutView(timeout=None)
        layout.add_item(make_themed_container(
            ui.TextDisplay(f"## {title}"),
            ui.TextDisplay(desc),
            make_separator(),
            make_banner_gallery(),
        ))
        await interaction.response.defer()
        await send_temp_v2(interaction, layout, delete_after=8, refresh_control=False)

    @app_commands.command(name="coffee", description="Support TAPI development")
    async def coffee(self, interaction: discord.Interaction):
        title = get_lan(interaction, "coffee_title")
        desc = get_lan(interaction, "coffee_description")
        btn_label = get_lan(interaction, "coffee_button")

        layout = ui.LayoutView(timeout=None)
        layout.add_item(make_themed_container(
            ui.TextDisplay(f"## {title}"),
            ui.TextDisplay(desc),
            make_separator(),
            make_banner_gallery(),
            ui.ActionRow(
                ui.Button(
                    label=btn_label,
                    url="https://buymeacoffee.com/cksxoo",
                    style=discord.ButtonStyle.link,
                )
            ),
        ))

        await interaction.response.send_message(view=layout)


async def setup(bot):
    await bot.add_cog(Other(bot))
    LOGGER.info("Other loaded!")
