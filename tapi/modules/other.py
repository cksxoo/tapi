import os
import discord
from discord import app_commands
from discord.ext import commands

from tapi.utils.language import get_lan
from tapi.utils.database import Database
from tapi import LOGGER, THEME_COLOR, APP_BANNER_URL
from tapi.utils.embed import send_temp_message

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
            title=get_lan(interaction.guild.id, "other_invite_title"),
            description=get_lan(interaction.guild.id, "other_invite_description").format(
                link=link
            ),
            color=THEME_COLOR,
        )
        embed.set_image(url=APP_BANNER_URL)
        await interaction.response.defer()
        await send_temp_message(interaction, embed, delete_after=8)

    @app_commands.command(name="language", description="Set the server language / 서버 언어 설정")
    @app_commands.choices(
        lang=[app_commands.Choice(name=lang, value=lang) for lang in lan_pack]
    )
    async def language(self, interaction: discord.Interaction, lang: str = None):
        if lang is None:
            files = "\n".join(lan_pack)
            embed = discord.Embed(
                title=get_lan(interaction.guild.id, "set_language_pack_list"),
                description=files,
                color=THEME_COLOR,
            )
            embed.set_image(url=APP_BANNER_URL)
            await interaction.response.defer()
            return await send_temp_message(interaction, embed, delete_after=8)

        if lang not in lan_pack:
            embed = discord.Embed(
                title=get_lan(interaction.guild.id, "set_language_pack_not_exist"),
                color=THEME_COLOR,
            )
            embed.set_image(url=APP_BANNER_URL)
            await interaction.response.defer()
            return await send_temp_message(interaction, embed)

        # 현재 길드 언어 설정 가져오기
        current_lang = self.database.get_guild_language(interaction.guild.id)

        # 새로운 언어 설정 저장 (길드별로)
        self.database.set_guild_language(interaction.guild.id, lang)

        # 임베드 메시지 생성
        if current_lang == "ko":  # 기본값인 경우
            embed = discord.Embed(
                title=get_lan(interaction.guild.id, "set_language_complete"),
                description=f"Server language: {lang}",
                color=THEME_COLOR,
            )
        else:
            embed = discord.Embed(
                title=get_lan(interaction.guild.id, "set_language_complete"),
                description=f"Server language: {current_lang} → {lang}",
                color=THEME_COLOR,
            )

        embed.set_image(url=APP_BANNER_URL)
        await interaction.response.defer()
        await send_temp_message(interaction, embed)


async def setup(bot):
    await bot.add_cog(Other(bot))
    LOGGER.info("Other loaded!")
