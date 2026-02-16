import discord
from discord import app_commands, ui
from discord.ext import commands

from tapi.utils.language import get_lan
from tapi import LOGGER, INFO_COLOR
from tapi.utils.v2_components import (
    make_themed_container, make_separator,
)


class HelpNavButton(ui.Button):
    """Help 페이지 네비게이션 버튼"""
    def __init__(self, label, style, target_page, disabled=False):
        super().__init__(label=label, style=style, disabled=disabled)
        self.target_page = target_page

    async def callback(self, interaction: discord.Interaction):
        view: HelpLayout = self.view
        if interaction.user.id != view.user_id:
            return await interaction.response.send_message(
                "This button can only be used by the user who executed the command.",
                ephemeral=True,
            )
        new_view = HelpLayout(interaction, view.user_id, page=self.target_page)
        new_view.message = view.message
        await interaction.response.edit_message(view=new_view)


PAGE_CONFIG = {
    "main": ("help_main_title", "help_main_description"),
    "music": ("help_music_title", "help_music_description"),
    "general": ("help_general_title", "help_general_description"),
}

PAGE_BUTTONS = [
    ("main", "Main"),
    ("music", "Music"),
    ("general", "General"),
]


class HelpLayout(ui.LayoutView):
    """V2 Help 메뉴 레이아웃"""
    def __init__(self, interaction, user_id, page="main"):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.page = page
        self.message = None

        title_key, desc_key = PAGE_CONFIG[page]
        title = get_lan(interaction, title_key)
        body = get_lan(interaction, desc_key)

        # 본문을 빈 줄 기준으로 분할하여 카테고리별 TextDisplay 생성
        items = [ui.TextDisplay(f"## {title}")]
        sections = [s.strip() for s in body.split("\n\n") if s.strip()]
        for i, section in enumerate(sections):
            items.append(ui.TextDisplay(section))
            if i < len(sections) - 1:
                items.append(make_separator())

        # 네비게이션 버튼 (현재 페이지는 disabled + green)
        nav_buttons = []
        for page_key, label in PAGE_BUTTONS:
            if page_key == page:
                nav_buttons.append(HelpNavButton(
                    label, discord.ButtonStyle.success, page_key, disabled=True
                ))
            else:
                nav_buttons.append(HelpNavButton(
                    label, discord.ButtonStyle.secondary, page_key
                ))

        items.append(make_separator())
        items.append(ui.ActionRow(*nav_buttons))

        self.add_item(make_themed_container(*items, accent_color=INFO_COLOR))

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.delete()
            except (discord.NotFound, discord.Forbidden):
                pass


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show help menu")
    async def help(self, interaction: discord.Interaction):
        """Show interactive help menu"""
        view = HelpLayout(interaction, interaction.user.id, page="main")
        await interaction.response.send_message(view=view)
        view.message = await interaction.original_response()


async def setup(bot):
    await bot.add_cog(Help(bot))
    LOGGER.info("Help loaded!")
