import discord
from discord import app_commands
from discord.ext import commands

from musicbot.utils.language import get_lan
from musicbot import LOGGER, COLOR_CODE


class ShardInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="shard", description="샤드 정보를 표시합니다")
    @app_commands.default_permissions(administrator=True)
    async def shard_info(self, interaction: discord.Interaction):
        """샤드 정보를 표시하는 명령어"""
        
        embed = discord.Embed(
            title="🔧 샤드 정보",
            color=COLOR_CODE,
        )
        
        # 현재 샤드 정보
        if hasattr(self.bot, 'shard_id') and self.bot.shard_id is not None:
            embed.add_field(
                name="현재 샤드 ID",
                value=f"{self.bot.shard_id}",
                inline=True,
            )
            embed.add_field(
                name="총 샤드 수",
                value=f"{self.bot.shard_count}",
                inline=True,
            )
        else:
            embed.add_field(
                name="샤딩 상태",
                value="샤딩이 비활성화됨",
                inline=True,
            )
        
        # 현재 샤드의 길드 수
        embed.add_field(
            name="이 샤드의 길드 수",
            value=f"{len(self.bot.guilds)}개",
            inline=True,
        )
        
        # 지연시간
        if hasattr(self.bot, 'latency'):
            embed.add_field(
                name="지연시간",
                value=f"{round(self.bot.latency * 1000)}ms",
                inline=True,
            )
        
        embed.set_footer(text=f"샤드 정보: {self.bot.shard_info}")
        
        await interaction.response.send_message(embed=embed)

    @commands.command(name="shardstats")
    @commands.is_owner()
    async def shard_stats(self, ctx):
        """소유자 전용: 모든 샤드의 상태를 표시 (텍스트 명령어)"""
        
        embed = discord.Embed(
            title="📊 전체 샤드 통계",
            color=COLOR_CODE,
        )
        
        if hasattr(self.bot, 'shard_id') and self.bot.shard_id is not None:
            embed.add_field(
                name="현재 샤드",
                value=f"샤드 {self.bot.shard_id}/{self.bot.shard_count}",
                inline=True,
            )
            embed.add_field(
                name="이 샤드 길드 수",
                value=f"{len(self.bot.guilds)}개",
                inline=True,
            )
            embed.add_field(
                name="지연시간",
                value=f"{round(self.bot.latency * 1000)}ms",
                inline=True,
            )
            
            # 음악 플레이어 정보
            player_count = 0
            for guild in self.bot.guilds:
                player = self.bot.lavalink.player_manager.get(guild.id)
                try:
                    if player.is_connected:
                        player_count += 1
                except Exception:
                    pass
            
            embed.add_field(
                name="활성 음악 플레이어",
                value=f"{player_count}개",
                inline=True,
            )
        else:
            embed.add_field(
                name="샤딩 상태",
                value="샤딩이 비활성화됨",
                inline=False,
            )
        
        embed.set_footer(text="이 정보는 현재 샤드의 상태만 표시합니다.")
        
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ShardInfo(bot))
    LOGGER.info("ShardInfo loaded!")
