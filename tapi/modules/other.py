import discord
from discord import app_commands, ui
from discord.ext import commands

from tapi.utils.language import get_lan
from tapi import LOGGER
from tapi.utils.database import Database
from tapi.utils.v2_components import (
    make_themed_container, make_banner_gallery, make_separator, send_temp_v2,
    StatusLayout,
)


class Other(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="invite", description="Send you a link for invite me")
    async def invite(self, interaction: discord.Interaction):
        link = f"https://discord.com/oauth2/authorize?client_id={self.bot.user.id}&permissions=37047296&scope=bot%20applications.commands"
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

    @app_commands.command(name="channel", description="Set or unset the music command channel")
    @app_commands.default_permissions(manage_guild=True)
    async def channel(self, interaction: discord.Interaction):
        db = Database()
        current_channel_id = str(interaction.channel.id)
        saved_channel_id = db.get_text_channel(interaction.guild.id)

        if saved_channel_id and str(saved_channel_id) == current_channel_id:
            # 이미 현재 채널로 설정되어 있으면 해제 (토글)
            db.set_text_channel(interaction.guild.id, None)
            text = get_lan(interaction, "channel_reset")
            layout = StatusLayout(title_text=text, style="success")
        else:
            # 현재 채널로 설정
            db.set_text_channel(interaction.guild.id, current_channel_id)
            text = get_lan(interaction, "channel_set").format(
                channel=f"<#{current_channel_id}>"
            )
            layout = StatusLayout(title_text=text, style="success")

        await interaction.response.send_message(view=layout, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Other(bot))
    LOGGER.info("Other loaded!")
