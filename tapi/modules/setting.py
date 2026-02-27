import discord
from discord import app_commands, ui
from discord.app_commands import Choice
from discord.ext import commands

from tapi.utils.language import get_lan
from tapi import LOGGER
from tapi.utils.database import Database
from tapi.utils.v2_components import make_themed_container

class SettingCmd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setting", description="Bot settings for this server")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(option="Choose a setting to configure")
    @app_commands.choices(option=[
        Choice(name="Auto Delete Messages Toggle", value="autodel"),
        Choice(name="Set/Unset Bot Channel", value="channel")
    ])
    async def setting(self, interaction: discord.Interaction, option: str):
        if option == "autodel":
            db = Database()
            current_state = db.get_autodel(interaction.guild.id)
            new_state = not current_state
            db.set_autodel(interaction.guild.id, new_state)
            
            if new_state:
                msg = get_lan(interaction, "setting_autodel_result_on")
            else:
                msg = get_lan(interaction, "setting_autodel_result_off")
                
            await interaction.response.send_message(msg, ephemeral=True)
            
        elif option == "channel":
            db = Database()
            current_bot_channel_id = db.get_channel(interaction.guild.id)
            current_channel = interaction.channel

            if current_bot_channel_id == current_channel.id:
                db.set_channel(interaction.guild.id, None)
                layout = ui.LayoutView(timeout=None)
                layout.add_item(make_themed_container(
                    ui.TextDisplay(f"### {get_lan(interaction, 'channel_unset_title')}"),
                    ui.TextDisplay(
                        get_lan(interaction, "channel_unset_description").format(
                            channel=current_channel.mention
                        )
                    ),
                ))
            else:
                db.set_channel(interaction.guild.id, current_channel.id)
                layout = ui.LayoutView(timeout=None)
                layout.add_item(make_themed_container(
                    ui.TextDisplay(f"### {get_lan(interaction, 'channel_set_title')}"),
                    ui.TextDisplay(
                        get_lan(interaction, "channel_set_description").format(
                            channel=current_channel.mention
                        )
                    ),
                ))

            await interaction.response.send_message(view=layout, ephemeral=True)

async def setup(bot):
    await bot.add_cog(SettingCmd(bot))
    LOGGER.info("Setting loaded!")
