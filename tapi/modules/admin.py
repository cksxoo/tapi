import discord
from discord import app_commands
from discord.ext import commands
import lavalink
import platform
import psutil
import math
import requests

from tapi.utils.language import get_lan
from tapi import LOGGER, THEME_COLOR, APP_NAME_TAG_VER, EXTENSIONS, DEBUG_SERVER


class Owners(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.color = THEME_COLOR
        self.error_color = 0xFF4A4A

    @app_commands.command()
    @app_commands.default_permissions(administrator=True)
    async def dev_help(self, interaction: discord.Interaction):
        """개발자용 도움말"""
        embed = discord.Embed(
            title=get_lan(interaction.user.id, "help_dev"),
            description=get_lan(interaction.user.id, "help_dev_description"),
            color=THEME_COLOR,
        )
        embed.add_field(
            name=get_lan(interaction.user.id, "help_dev_serverlist_command"),
            value=get_lan(interaction.user.id, "help_dev_serverlist_info"),
            inline=False,
        )
        embed.add_field(
            name=get_lan(interaction.user.id, "help_dev_modules_command"),
            value=get_lan(interaction.user.id, "help_dev_modules_info"),
            inline=False,
        )
        embed.add_field(
            name=get_lan(interaction.user.id, "help_dev_load_command"),
            value=get_lan(interaction.user.id, "help_dev_load_info"),
            inline=False,
        )
        embed.add_field(
            name=get_lan(interaction.user.id, "help_dev_unload_command"),
            value=get_lan(interaction.user.id, "help_dev_unload_info"),
            inline=False,
        )
        embed.add_field(
            name=get_lan(interaction.user.id, "help_dev_reload_command"),
            value=get_lan(interaction.user.id, "help_dev_reload_info"),
            inline=False,
        )
        embed.add_field(
            name=get_lan(interaction.user.id, "help_dev_serverinfo_command"),
            value=get_lan(interaction.user.id, "help_dev_serverinfo_info"),
            inline=False,
        )
        embed.add_field(
            name=get_lan(interaction.user.id, "help_dev_broadcast_command"),
            value=get_lan(interaction.user.id, "help_dev_broadcast_info"),
            inline=False,
        )
        embed.set_footer(text=APP_NAME_TAG_VER)
        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    @app_commands.default_permissions(administrator=True)
    async def load(self, interaction: discord.Interaction, module: str):
        """모듈을 로드합니다."""
        try:
            await self.bot.load_extension(f"tapi.modules.{module}")
            LOGGER.info(f"로드 성공!\n모듈: {module}")
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "owners_load_success"),
                description=get_lan(interaction.user.id, "owners_module").format(
                    module=module
                ),
                color=self.color,
            )
            if f"*~~{module}~~*" in EXTENSIONS:
                EXTENSIONS[EXTENSIONS.index(f"*~~{module}~~*")] = module
            else:
                EXTENSIONS.append(module)
        except Exception as error:
            LOGGER.error(f"로드 실패!\n에러: {error}")
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "owners_load_fail"),
                description=get_lan(interaction.user.id, "owners_error").format(
                    error=error
                ),
                color=self.error_color,
            )
        embed.set_footer(text=APP_NAME_TAG_VER)
        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    @app_commands.default_permissions(administrator=True)
    async def reload(self, interaction: discord.Interaction, module: str):
        """모듈을 리로드합니다."""
        try:
            await self.bot.reload_extension(f"tapi.modules.{module}")
            LOGGER.info(f"리로드 성공!\n모듈: {module}")
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "owners_reload_success"),
                description=get_lan(interaction.user.id, "owners_module").format(
                    module=module
                ),
                color=self.color,
            )
        except Exception as error:
            LOGGER.error(f"리로드 실패!\n에러: {error}")
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "owners_reload_fail"),
                description=f"에러: {error}",
                color=self.error_color,
            )
            if module in EXTENSIONS:
                EXTENSIONS[EXTENSIONS.index(module)] = f"*~~{module}~~*"
        embed.set_footer(text=APP_NAME_TAG_VER)
        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    @app_commands.default_permissions(administrator=True)
    async def unload(self, interaction: discord.Interaction, module: str):
        """모듈을 언로드합니다."""
        try:
            await self.bot.unload_extension(f"tapi.modules.{module}")
            LOGGER.info(f"언로드 성공!\n모듈: {module}")
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "owners_unload_success"),
                description=get_lan(interaction.user.id, "owners_module").format(
                    module=module
                ),
                color=self.color,
            )
            if module in EXTENSIONS:
                EXTENSIONS[EXTENSIONS.index(module)] = f"*~~{module}~~*"
        except Exception as error:
            LOGGER.error(f"언로드 실패!\n에러: {error}")
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "owners_unload_fail"),
                description=f"에러: {error}",
                color=self.error_color,
            )
        embed.set_footer(text=APP_NAME_TAG_VER)
        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    @app_commands.default_permissions(administrator=True)
    async def module_list(self, interaction: discord.Interaction):
        """모든 모듈들의 이름을 알려줘요!"""
        modulenum = sum(1 for m in EXTENSIONS if not m.startswith("*~~"))
        modulenum = get_lan(interaction.user.id, "owners_loaded_modules_len").format(
            modulenum=modulenum
        )
        e1 = "\n".join(EXTENSIONS)
        embed = discord.Embed(
            title=get_lan(interaction.user.id, "owners_modules_list"), color=THEME_COLOR
        )
        embed.add_field(name=modulenum, value=e1, inline=False)
        embed.set_footer(text=APP_NAME_TAG_VER)
        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    @app_commands.default_permissions(administrator=True)
    async def serverinfo(self, interaction: discord.Interaction):
        """봇 서버의 사양을 알려줘요!"""
        embed = discord.Embed(
            title=get_lan(interaction.user.id, "owners_server_info"), color=THEME_COLOR
        )
        embed.add_field(name="Platform", value=platform.platform(), inline=False)
        embed.add_field(name="Kernel", value=platform.version(), inline=False)
        embed.add_field(name="Architecture", value=platform.machine(), inline=False)
        embed.add_field(
            name="CPU Usage", value=f"{psutil.cpu_percent()}%", inline=False
        )
        memorystr = f"{round((psutil.virtual_memory().used / (1024.0 ** 3)), 1)}GB / {round((psutil.virtual_memory().total / (1024.0 ** 3)), 1)}GB"
        embed.add_field(name="Memory Usage", value=memorystr, inline=False)
        embed.add_field(
            name="Python Ver",
            value=f"{platform.python_implementation()} {platform.python_version()}",
            inline=False,
        )
        embed.add_field(name="discord.py Ver", value=discord.__version__, inline=False)
        embed.add_field(
            name="Lavalink.py Ver", value=lavalink.__version__, inline=False
        )
        embed.add_field(
            name="Ping", value=f"{round(self.bot.latency * 1000)}ms", inline=False
        )
        embed.set_footer(text=APP_NAME_TAG_VER)
        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    @app_commands.default_permissions(administrator=True)
    async def server_list(self, interaction: discord.Interaction):
        """봇이 들어가있는 모든 서버 리스트를 출력합니다."""
        try:
            # 응답이 아직 전송되지 않은 경우에만 defer 호출
            if not interaction.response.is_done():
                await interaction.response.defer()

            page = 10
            if len(self.bot.guilds) <= page:
                embed = discord.Embed(
                    title=get_lan(
                        interaction.user.id, "owners_server_list_title"
                    ).format(BOT_NAME=self.bot.user.name),
                    description=get_lan(
                        interaction.user.id, "owners_server_list_description"
                    ).format(
                        server_count=len(self.bot.guilds),
                        members_count=len(self.bot.users),
                    ),
                    color=THEME_COLOR,
                )
                srvr = "\n".join(
                    get_lan(interaction.user.id, "owners_server_list_info").format(
                        server_name=i.name, server_members_count=i.member_count
                    )
                    for i in self.bot.guilds
                )
                embed.add_field(name="​", value=srvr, inline=False)
                embed.set_footer(text=APP_NAME_TAG_VER)
                return await interaction.edit_original_response(embed=embed)

            guilds = sorted(self.bot.guilds, key=lambda x: (-x.member_count, x.name))
            allpage = math.ceil(len(guilds) / page)

            embeds = []
            for i in range(allpage):
                srvr = "\n".join(
                    get_lan(interaction.user.id, "owners_server_list_info").format(
                        server_name=guild.name, server_members_count=guild.member_count
                    )
                    for guild in guilds[i * page : (i + 1) * page]
                )

                embed = discord.Embed(
                    title=get_lan(
                        interaction.user.id, "owners_server_list_title"
                    ).format(BOT_NAME=self.bot.user.name),
                    description=get_lan(
                        interaction.user.id, "owners_server_list_description2"
                    ).format(
                        server_count=len(self.bot.guilds),
                        members_count=len(self.bot.users),
                        servers=srvr,
                    ),
                    color=THEME_COLOR,
                ).set_footer(
                    text=f"{get_lan(interaction.user.id, 'owners_page')} {i+1}/{allpage}\n{APP_NAME_TAG_VER}"
                )
                embeds.append(embed)

            await interaction.edit_original_response(
                embed=embeds[0], view=ServerListPaginator(embeds)
            )
        except discord.errors.NotFound:
            LOGGER.error("Interaction has expired.")
        except discord.errors.InteractionResponded:
            LOGGER.error("This interaction has already been responded to")
        except Exception as e:
            LOGGER.error(f"An error occurred in server_list: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "An error occurred while processing your request."
                )
            else:
                await interaction.followup.send(
                    "An error occurred while processing your request."
                )

    @app_commands.command()
    @app_commands.default_permissions(administrator=True)
    async def public_ip(self, interaction: discord.Interaction):
        """서버의 공인 IP를 알려줘요!"""
        public_ip = requests.get("https://api.ipify.org").text
        embed = discord.Embed(title="Public IP", color=THEME_COLOR)
        embed.add_field(name="IP", value=public_ip, inline=False)
        embed.set_footer(text=APP_NAME_TAG_VER)
        await interaction.response.send_message(embed=embed)


class ServerListPaginator(discord.ui.View):
    def __init__(self, embeds):
        super().__init__(timeout=60)
        self.embeds = embeds
        self.current_page = 0

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.gray)
    async def previous_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.current_page = (self.current_page - 1) % len(self.embeds)
        await interaction.response.edit_message(embed=self.embeds[self.current_page])

    @discord.ui.button(label="Next", style=discord.ButtonStyle.gray)
    async def next_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.current_page = (self.current_page + 1) % len(self.embeds)
        await interaction.response.edit_message(embed=self.embeds[self.current_page])


async def setup(bot):
    await bot.add_cog(Owners(bot))
    LOGGER.info("Owners Loaded!")
