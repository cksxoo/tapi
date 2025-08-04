import discord
from discord import app_commands
from discord.ext import commands

from tapi.utils.language import get_lan
from tapi import LOGGER, APP_NAME_TAG_VER, THEME_COLOR


class HelpView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.message = None

    @discord.ui.button(label="🎵 Music", style=discord.ButtonStyle.primary, custom_id="music")
    async def music_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This button can only be used by the user who executed the command.", ephemeral=True)
        
        embed = discord.Embed(
            title=get_lan(self.user_id, "help_music_title"),
            description=get_lan(self.user_id, "help_music_description"),
            color=THEME_COLOR,
        )
        embed.set_footer(text=APP_NAME_TAG_VER)
        
        view = BackToMainView(self.user_id)
        view.message = interaction.message
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="⚙️ General", style=discord.ButtonStyle.secondary, custom_id="general")
    async def general_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This button can only be used by the user who executed the command.", ephemeral=True)
        
        embed = discord.Embed(
            title=get_lan(self.user_id, "help_general_title"),
            description=get_lan(self.user_id, "help_general_description"),
            color=THEME_COLOR,
        )
        embed.set_footer(text=APP_NAME_TAG_VER)
        
        view = BackToMainView(self.user_id)
        view.message = interaction.message
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🌍 Language", style=discord.ButtonStyle.secondary, custom_id="language")
    async def language_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This button can only be used by the user who executed the command.", ephemeral=True)
        
        embed = discord.Embed(
            title=get_lan(self.user_id, "help_language_title"),
            description=get_lan(self.user_id, "help_language_description"),
            color=THEME_COLOR,
        )
        embed.set_footer(text=APP_NAME_TAG_VER)
        
        view = BackToMainView(self.user_id)
        view.message = interaction.message
        await interaction.response.edit_message(embed=embed, view=view)

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.delete()
            except:
                pass


class BackToMainView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.message = None

    @discord.ui.button(label="🏠 Main", style=discord.ButtonStyle.success, custom_id="home")
    async def home_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This button can only be used by the user who executed the command.", ephemeral=True)
        
        embed = discord.Embed(
            title=get_lan(self.user_id, "help_main_title").format(bot_name=interaction.guild.me.display_name if interaction.guild else "Bot"),
            description=get_lan(self.user_id, "help_main_description"),
            color=THEME_COLOR,
        )
        embed.set_image(url="https://github.com/cksxoo/tapi/blob/main/docs/discord.png?raw=true&v=2")
        
        view = HelpView(self.user_id)
        view.message = interaction.message
        await interaction.response.edit_message(embed=embed, view=view)

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.delete()
            except:
                pass


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show help menu")
    async def help(self, interaction: discord.Interaction):
        """Show interactive help menu"""
        embed = discord.Embed(
            title=get_lan(interaction.user.id, "help_main_title").format(bot_name=self.bot.user.name),
            description=get_lan(interaction.user.id, "help_main_description"),
            color=THEME_COLOR,
        )
        embed.set_image(url="https://github.com/cksxoo/tapi/blob/main/docs/discord.png?raw=true&v=2")
        
        view = HelpView(interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()


async def setup(bot):
    await bot.add_cog(Help(bot))
    LOGGER.info("Help loaded!")