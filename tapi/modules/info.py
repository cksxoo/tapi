import discord
from discord import app_commands
from discord.ext import commands

from tapi.utils.language import get_lan
from tapi import LOGGER, APP_NAME_TAG_VER, THEME_COLOR, ABOUT_BOT


class About(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="about", description="Let me tell you about me!")
    async def about(self, interaction: discord.Interaction):
        player_server_count = 0
        for guild in self.bot.guilds:
            player = self.bot.lavalink.player_manager.get(guild.id)
            try:
                if player.is_connected:
                    player_server_count += 1
            except Exception:
                pass

        players = 0
        playing_players = 0
        for node in self.bot.lavalink.node_manager.nodes:
            stats = node.stats
            players += stats.players
            playing_players += stats.playing_players

        embed = discord.Embed(
            title=get_lan(interaction.user.id, "about_bot_info"),
            description=ABOUT_BOT,
            color=THEME_COLOR,
        )
        # embed.add_field(
        #     name="Github",
        #     value="[music_bot](https://github.com/leechanwoo-kor/music_bot)",
        #     inline=False,
        # )
        embed.add_field(
            name=get_lan(interaction.user.id, "about_guild_count"),
            value=str(len(self.bot.guilds)),
            inline=True,
        )
        embed.add_field(
            name="샤드 정보",
            value=self.bot.shard_info,
            inline=True,
        )
        embed.add_field(
            name=get_lan(interaction.user.id, "about_number_of_music_playback_servers"),
            value=f"lavalink: {players}({playing_players} playing)\nvoice channel count: {player_server_count} playing",
            inline=True,
        )
        embed.set_footer(text=APP_NAME_TAG_VER)
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(About(bot))
    LOGGER.info("About loaded!")
