import os
import discord
from discord import app_commands
from discord.ext import commands

from tapi.utils.language import get_lan
from tapi.utils.database import Database
from tapi import LOGGER, APP_NAME_TAG_VER, THEME_COLOR
from tapi.modules.player import send_temp_message

lan_pack = [
    file.replace(".json", "")
    for file in os.listdir("tapi/languages")
    if file.endswith(".json")
]


class Other(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.database = Database()

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

    @app_commands.command(name="language", description="Apply the language pack.")
    @app_commands.choices(
        lang=[app_commands.Choice(name=lang, value=lang) for lang in lan_pack]
    )
    async def language(self, interaction: discord.Interaction, lang: str = None):
        if lang is None:
            files = "\n".join(lan_pack)
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "set_language_pack_list"),
                description=files,
                color=THEME_COLOR,
            )
            embed.set_footer(text=APP_NAME_TAG_VER)
            await interaction.response.defer()
            return await send_temp_message(interaction, embed)

        if lang not in lan_pack:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "set_language_pack_not_exist"),
                color=THEME_COLOR,
            )
            embed.set_footer(text=APP_NAME_TAG_VER)
            await interaction.response.defer()
            return await send_temp_message(interaction, embed)

        # 현재 사용자 언어 설정 가져오기
        current_lang = self.database.get_user_language(interaction.user.id)
        
        # 새로운 언어 설정 저장
        self.database.set_user_language(interaction.user.id, lang)
        
        # 임베드 메시지 생성
        if current_lang == "kr":  # 기본값인 경우
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "set_language_complete"),
                description=f"{lang}",
                color=THEME_COLOR,
            )
        else:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "set_language_complete"),
                description=f"{current_lang} --> {lang}",
                color=THEME_COLOR,
            )

        embed.set_footer(text=APP_NAME_TAG_VER)
        await interaction.response.defer()
        await send_temp_message(interaction, embed)


async def setup(bot):
    await bot.add_cog(Other(bot))
    LOGGER.info("Other loaded!")
