"""
봇 통계를 top.gg 및 koreanbots.dev에 자동 업데이트하는 유틸리티
"""
import aiohttp
import asyncio
from typing import Optional
from tapi import LOGGER


class BotStatsUpdater:
    """봇 리스팅 사이트에 서버 수 업데이트"""

    def __init__(
        self, bot_id: int, topgg_token: Optional[str], koreanbot_token: Optional[str]
    ):
        self.bot_id = bot_id
        self.topgg_token = topgg_token
        self.koreanbot_token = koreanbot_token
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """aiohttp 세션 가져오기 (재사용)"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def update_topgg(
        self, guild_count: int, shard_count: Optional[int] = None
    ) -> bool:
        """
        top.gg에 서버 수 업데이트

        Args:
            guild_count: 총 서버 수
            shard_count: 샤드 수 (선택사항)

        Returns:
            bool: 성공 여부
        """
        if not self.topgg_token:
            LOGGER.debug("top.gg token not configured, skipping update")
            return False

        try:
            session = await self._get_session()
            url = f"https://top.gg/api/bots/{self.bot_id}/stats"
            headers = {"Authorization": self.topgg_token}

            data = {"server_count": guild_count}
            if shard_count:
                data["shard_count"] = shard_count

            async with session.post(url, json=data, headers=headers) as resp:
                if resp.status == 200:
                    LOGGER.info(f"✅ top.gg stats updated: {guild_count} guilds")
                    return True
                else:
                    error_text = await resp.text()
                    LOGGER.error(
                        f"❌ top.gg update failed ({resp.status}): {error_text}"
                    )
                    return False

        except Exception as e:
            LOGGER.error(f"❌ Error updating top.gg stats: {e}")
            return False

    async def update_koreanbots(
        self, guild_count: int, shard_count: Optional[int] = None
    ) -> bool:
        """
        koreanbots.dev에 서버 수 업데이트

        Args:
            guild_count: 총 서버 수
            shard_count: 샤드 수 (선택사항)

        Returns:
            bool: 성공 여부
        """
        if not self.koreanbot_token:
            LOGGER.debug("koreanbots.dev token not configured, skipping update")
            return False

        try:
            session = await self._get_session()
            url = f"https://koreanbots.dev/api/v2/bots/{self.bot_id}/stats"
            headers = {"Authorization": self.koreanbot_token}

            data = {"servers": guild_count}
            if shard_count:
                data["shards"] = shard_count

            async with session.post(url, json=data, headers=headers) as resp:
                if resp.status == 200:
                    LOGGER.info(f"✅ koreanbots.dev stats updated: {guild_count} guilds")
                    return True
                else:
                    error_text = await resp.text()
                    LOGGER.error(
                        f"❌ koreanbots.dev update failed ({resp.status}): {error_text}"
                    )
                    return False

        except Exception as e:
            LOGGER.error(f"❌ Error updating koreanbots.dev stats: {e}")
            return False

    async def update_all(
        self, guild_count: int, shard_count: Optional[int] = None
    ) -> dict:
        """
        모든 봇 리스팅 사이트에 업데이트

        Args:
            guild_count: 총 서버 수
            shard_count: 샤드 수 (선택사항)

        Returns:
            dict: 각 사이트별 업데이트 결과
        """
        results = {}

        # 병렬로 모든 사이트 업데이트
        topgg_task = self.update_topgg(guild_count, shard_count)
        koreanbots_task = self.update_koreanbots(guild_count, shard_count)

        results["topgg"], results["koreanbots"] = await asyncio.gather(
            topgg_task, koreanbots_task, return_exceptions=True
        )

        return results

    async def close(self):
        """세션 종료"""
        if self.session and not self.session.closed:
            await self.session.close()
            LOGGER.debug("BotStatsUpdater session closed")
