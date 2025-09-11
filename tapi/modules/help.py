import discord
from discord import app_commands
from discord.ext import commands

from tapi.utils.language import get_lan
from tapi import LOGGER, THEME_COLOR, APP_BANNER_URL


class HelpView(discord.ui.View):
    def __init__(self, guild_id, user_id):
        super().__init__(timeout=120)
        self.guild_id = guild_id
        self.user_id = user_id
        self.message = None

    @discord.ui.button(label="🎵 Music", style=discord.ButtonStyle.primary, custom_id="music")
    async def music_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This button can only be used by the user who executed the command.", ephemeral=True)
        
        embed = discord.Embed(
            title=get_lan(self.guild_id, "help_music_title"),
            description=get_lan(self.guild_id, "help_music_description"),
            color=THEME_COLOR,
        )
        embed.set_image(url=APP_BANNER_URL)
        
        view = BackToMainView(self.guild_id, self.user_id)
        view.message = interaction.message
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="⚙️ General", style=discord.ButtonStyle.secondary, custom_id="general")
    async def general_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This button can only be used by the user who executed the command.", ephemeral=True)
        
        embed = discord.Embed(
            title=get_lan(self.guild_id, "help_general_title"),
            description=get_lan(self.guild_id, "help_general_description"),
            color=THEME_COLOR,
        )
        embed.set_image(url=APP_BANNER_URL)
        
        view = BackToMainView(self.guild_id, self.user_id)
        view.message = interaction.message
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🌍 Language", style=discord.ButtonStyle.secondary, custom_id="language")
    async def language_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This button can only be used by the user who executed the command.", ephemeral=True)
        
        embed = discord.Embed(
            title=get_lan(self.guild_id, "help_language_title"),
            description=get_lan(self.guild_id, "help_language_description"),
            color=THEME_COLOR,
        )
        embed.set_image(url=APP_BANNER_URL)
        
        view = BackToMainView(self.guild_id, self.user_id)
        view.message = interaction.message
        await interaction.response.edit_message(embed=embed, view=view)

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.delete()
            except discord.NotFound:
                pass
            except discord.Forbidden:
                pass


class BackToMainView(discord.ui.View):
    def __init__(self, guild_id, user_id):
        super().__init__(timeout=120)
        self.guild_id = guild_id
        self.user_id = user_id
        self.message = None

    @discord.ui.button(label="🏠 Main", style=discord.ButtonStyle.success, custom_id="home")
    async def home_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This button can only be used by the user who executed the command.", ephemeral=True)
        
        embed = discord.Embed(
            title=get_lan(self.guild_id, "help_main_title"),
            description=get_lan(self.guild_id, "help_main_description"),
            color=THEME_COLOR,
        )
        embed.set_image(url=APP_BANNER_URL)
        
        view = HelpView(self.guild_id, self.user_id)
        view.message = interaction.message
        await interaction.response.edit_message(embed=embed, view=view)

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.delete()
            except discord.NotFound:
                pass
            except discord.Forbidden:
                pass


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show help menu")
    async def help(self, interaction: discord.Interaction):
        """Show interactive help menu"""
        embed = discord.Embed(
            title=get_lan(interaction.guild.id, "help_main_title"),
            description=get_lan(interaction.guild.id, "help_main_description"),
            color=THEME_COLOR,
        )
        embed.set_image(url=APP_BANNER_URL)
        
        view = HelpView(interaction.guild.id, interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()


async def setup(bot):
    await bot.add_cog(Help(bot))
    LOGGER.info("Help loaded!")