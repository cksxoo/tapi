import discord
import psutil
import datetime
from discord import app_commands
from discord.ext import commands, tasks

from musicbot.utils.language import get_lan
from musicbot.utils.redis_manager import redis_manager
from musicbot import LOGGER, COLOR_CODE

class ShardInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.process = psutil.Process()
        redis_manager.connect()
        self.update_redis_status.start()

    def cog_unload(self):
        self.update_redis_status.cancel()

    shard_group = app_commands.Group(name="shard", description="샤드 관련 명령어")

    @tasks.loop(seconds=15)
    async def update_redis_status(self):
        await self.bot.wait_until_ready()
        if not hasattr(self.bot, 'shard_id') or self.bot.shard_id is None:
            return

        if not self.bot.lavalink:
            return

        player_count = 0
        for guild in self.bot.guilds:
            player = self.bot.lavalink.player_manager.get(guild.id)
            if player and player.is_connected:
                player_count += 1

        latency = self.bot.latency
        latency_ms = round(latency * 1000) if latency != float('inf') else -1

        data = {
            "guild_count": len(self.bot.guilds),
            "latency": latency_ms,
            "memory_usage": round(self.process.memory_info().rss / (1024 * 1024), 2),
            "player_count": player_count,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        redis_manager.update_shard_status(self.bot.shard_id, data)

    @shard_group.command(name="current", description="현재 샤드의 정보를 표시합니다.")
    @app_commands.default_permissions(administrator=True)
    async def shard_info(self, interaction: discord.Interaction):
        """현재 샤드의 정보를 표시하는 명령어"""
        embed = discord.Embed(
            title=f"🔧 샤드 #{self.bot.shard_id} 정보",
            color=COLOR_CODE,
        )

        if hasattr(self.bot, 'shard_id') and self.bot.shard_id is not None:
            embed.add_field(name="총 샤드 수", value=f"{self.bot.shard_count}", inline=True)
            embed.add_field(name="이 샤드의 길드 수", value=f"{len(self.bot.guilds)}개", inline=True)
            latency = self.bot.latency
            latency_ms = f"{round(latency * 1000)}ms" if latency != float('inf') else "∞"
            embed.add_field(name="지연시간", value=latency_ms, inline=True)
            
            player_count = 0
            for guild in self.bot.guilds:
                player = self.bot.lavalink.player_manager.get(guild.id)
                if player and player.is_connected:
                    player_count += 1
            embed.add_field(name="활성 플레이어", value=f"{player_count}개", inline=True)
            
            memory_usage = self.process.memory_info().rss / (1024 * 1024)
            embed.add_field(name="메모리 사용량", value=f"{memory_usage:.2f} MB", inline=True)

        else:
            embed.add_field(name="샤딩 상태", value="샤딩이 비활성화됨", inline=False)

        await interaction.response.send_message(embed=embed)

    @shard_group.command(name="all", description="모든 샤드의 통합 정보를 표시합니다.")
    @app_commands.default_permissions(administrator=True)
    async def all_shards_info(self, interaction: discord.Interaction):
        """모든 샤드의 정보를 취합하여 표시하는 명령어"""
        await interaction.response.defer(thinking=True)

        all_statuses = redis_manager.get_all_shard_statuses()
        if not all_statuses:
            await interaction.followup.send("샤드 정보를 가져올 수 없습니다. Redis 서버를 확인해주세요.")
            return

        embed = discord.Embed(
            title="📊 모든 샤드 통합 정보",
            color=COLOR_CODE,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        total_guilds = 0
        total_players = 0
        total_memory = 0
        active_shards = 0
        latencies = []

        shard_details = ""
        now = datetime.datetime.now(datetime.timezone.utc)

        for shard_id in range(self.bot.shard_count):
            status = all_statuses.get(shard_id)
            if status:
                last_updated = now - datetime.datetime.fromisoformat(status['timestamp'])
                if last_updated.total_seconds() < 45:
                    # 온라인 상태
                    shard_details += f"🟢 **샤드 #{shard_id}** (온라인)\n"
                    total_guilds += status['guild_count']
                    total_players += status['player_count']
                    total_memory += status['memory_usage']
                    latencies.append(status['latency'])
                    active_shards += 1
                else:
                    # 오프라인 상태
                    shard_details += f"🔴 **샤드 #{shard_id}** (오프라인 - {int(last_updated.total_seconds())}초 전 응답)\n"
            else:
                # 데이터 없음
                shard_details += f"⚫ **샤드 #{shard_id}** (응답 없음)\n"
            
            if status and last_updated.total_seconds() < 45:
                shard_details += f"> 길드: {status['guild_count']}개 | 플레이어: {status['player_count']}개 | 지연: {status['latency']}ms | 메모리: {status['memory_usage']}MB\n\n"
            else:
                shard_details += f"> 마지막 확인 시간: {datetime.datetime.fromisoformat(status['timestamp']).strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n" if status else "> 데이터를 찾을 수 없습니다.\n\n"

        avg_latency = sum(latencies) / len(latencies) if latencies else 0

        embed.add_field(
            name="요약",
            value=f"- 활성 샤드: {active_shards}/{self.bot.shard_count}\n"
                  f"- 총 길드: {total_guilds}개\n"
                  f"- 총 플레이어: {total_players}개\n"
                  f"- 평균 지연: {avg_latency:.2f}ms\n"
                  f"- 총 메모리: {total_memory:.2f}MB",
            inline=False
        )
        embed.add_field(
            name="샤드별 상세 정보",
            value=shard_details if shard_details else "정보 없음",
            inline=False
        )

        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ShardInfo(bot))
    LOGGER.info("ShardInfo loaded!")