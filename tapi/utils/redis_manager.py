import json
import os
from tapi import LOGGER

try:
    import redis
    import redis.asyncio as aioredis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    LOGGER.warning("Redis is not available. Some features may be disabled.")


class RedisManager:
    def __init__(self):
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = 6379
        self.redis_db = 0
        self.redis_client = None
        self._async_client = None
        self.shard_stats_key_prefix = "shard_stats:"
        self.active_players_key_prefix = "active_players:"
        self.bot_guilds_key_prefix = "bot_guilds:"
        self.playback_state_key_prefix = "playback_state:"  # 점검 시 재생 상태 저장용
        self.shard_status_ttl = 60 * 10  # 10분
        self.active_player_ttl = 60  # 1분 (자주 업데이트되므로 짧게)
        self.playback_state_ttl = 60 * 10  # 10분 (점검 동안 유지)
        self.available = REDIS_AVAILABLE

    def connect(self):
        """Redis 서버에 연결합니다."""
        if not self.available:
            LOGGER.warning("Redis is not available. Skipping connection.")
            return False

        try:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                decode_responses=True,  # 응답을 자동으로 UTF-8로 디코딩
            )
            self.redis_client.ping()
            LOGGER.info("Successfully connected to Redis.")
            return True
        except redis.exceptions.ConnectionError as e:
            LOGGER.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
            return False
        except Exception as e:
            LOGGER.error(f"Unexpected error connecting to Redis: {e}")
            self.redis_client = None
            return False

    def get_client(self):
        """Redis 클라이언트 인스턴스를 반환합니다."""
        if not self.redis_client:
            self.connect()
        return self.redis_client

    def update_shard_status(self, shard_id: int, data: dict):
        """특정 샤드의 상태 정보를 업데이트하고 TTL을 설정합니다."""
        if not self.available:
            LOGGER.debug("Redis not available, skipping shard status update")
            return

        client = self.get_client()
        if client:
            try:
                key = f"{self.shard_stats_key_prefix}{shard_id}"
                client.set(key, json.dumps(data), ex=self.shard_status_ttl)
            except redis.exceptions.RedisError as e:
                LOGGER.error(f"Failed to update shard status in Redis: {e}")
            except Exception as e:
                LOGGER.error(f"Unexpected error updating shard status: {e}")

    def get_all_shard_statuses(self) -> dict:
        """모든 샤드의 상태 정보를 가져옵니다."""
        if not self.available:
            LOGGER.debug("Redis not available, returning empty shard statuses")
            return {}

        client = self.get_client()
        if client:
            try:
                shard_keys = []
                cursor = "0"
                while cursor != 0:
                    cursor, keys = client.scan(
                        cursor=cursor,
                        match=f"{self.shard_stats_key_prefix}*",
                        count=100,
                    )
                    shard_keys.extend(keys)

                if not shard_keys:
                    return {}

                raw_data = client.mget(shard_keys)
                statuses = {}
                for i, key in enumerate(shard_keys):
                    shard_id_str = key.split(":")[-1]
                    if raw_data[i]:
                        statuses[int(shard_id_str)] = json.loads(raw_data[i])
                return statuses
            except redis.exceptions.RedisError as e:
                LOGGER.error(f"Failed to get all shard statuses from Redis: {e}")
                return {}
            except (ValueError, IndexError) as e:
                LOGGER.error(f"Error parsing shard status from Redis: {e}")
                return {}
            except Exception as e:
                LOGGER.error(f"Unexpected error getting shard statuses: {e}")
                return {}
        return {}

    def update_active_players(self, shard_id: int, active_players_data: list):
        """활성 플레이어 정보를 Redis에 업데이트합니다."""
        if not self.available:
            LOGGER.debug("Redis not available, skipping active players update")
            return

        client = self.get_client()
        if client:
            try:
                key = f"{self.active_players_key_prefix}{shard_id}"
                client.set(
                    key, json.dumps(active_players_data), ex=self.active_player_ttl
                )
                LOGGER.debug(
                    f"Updated {len(active_players_data)} active players for shard {shard_id}"
                )
            except redis.exceptions.RedisError as e:
                LOGGER.error(f"Failed to update active players in Redis: {e}")
            except Exception as e:
                LOGGER.error(f"Unexpected error updating active players: {e}")

    def update_bot_guilds(self, shard_id: int, guild_ids: list):
        """봇이 속한 길드 ID 목록을 Redis에 저장합니다."""
        if not self.available:
            return

        client = self.get_client()
        if client:
            try:
                key = f"{self.bot_guilds_key_prefix}{shard_id}"
                client.set(key, json.dumps(guild_ids), ex=self.active_player_ttl)
            except Exception as e:
                LOGGER.error(f"Failed to update bot guilds in Redis: {e}")

    def get_all_active_players(self) -> dict:
        """모든 샤드의 활성 플레이어 정보를 가져옵니다."""
        if not self.available:
            LOGGER.debug("Redis not available, returning empty active players")
            return {}

        client = self.get_client()
        if client:
            try:
                player_keys = []
                cursor = "0"
                while cursor != 0:
                    cursor, keys = client.scan(
                        cursor=cursor,
                        match=f"{self.active_players_key_prefix}*",
                        count=100,
                    )
                    player_keys.extend(keys)

                if not player_keys:
                    return {}

                raw_data = client.mget(player_keys)
                all_players = {}
                for i, key in enumerate(player_keys):
                    shard_id_str = key.split(":")[-1]
                    if raw_data[i]:
                        all_players[int(shard_id_str)] = json.loads(raw_data[i])
                return all_players
            except redis.exceptions.RedisError as e:
                LOGGER.error(f"Failed to get active players from Redis: {e}")
                return {}
            except (ValueError, IndexError) as e:
                LOGGER.error(f"Error parsing active players from Redis: {e}")
                return {}
            except Exception as e:
                LOGGER.error(f"Unexpected error getting active players: {e}")
                return {}
        return {}

    def save_playback_state(self, shard_id: int, playback_states: list):
        """점검 전 재생 상태를 Redis에 저장합니다."""
        if not self.available:
            LOGGER.debug("Redis not available, skipping playback state save")
            return

        client = self.get_client()
        if client:
            try:
                key = f"{self.playback_state_key_prefix}{shard_id}"
                client.set(key, json.dumps(playback_states), ex=self.playback_state_ttl)
                LOGGER.info(
                    f"Saved playback state for {len(playback_states)} players on shard {shard_id}"
                )
            except redis.exceptions.RedisError as e:
                LOGGER.error(f"Failed to save playback state in Redis: {e}")
            except Exception as e:
                LOGGER.error(f"Unexpected error saving playback state: {e}")

    def get_playback_states(self, shard_id: int) -> list:
        """점검 후 저장된 재생 상태를 가져옵니다."""
        if not self.available:
            LOGGER.debug("Redis not available, returning empty playback states")
            return []

        client = self.get_client()
        if client:
            try:
                key = f"{self.playback_state_key_prefix}{shard_id}"
                data = client.get(key)
                if data:
                    states = json.loads(data)
                    LOGGER.info(
                        f"Retrieved playback state for {len(states)} players on shard {shard_id}"
                    )
                    return states
                return []
            except redis.exceptions.RedisError as e:
                LOGGER.error(f"Failed to get playback state from Redis: {e}")
                return []
            except (ValueError, json.JSONDecodeError) as e:
                LOGGER.error(f"Error parsing playback state from Redis: {e}")
                return []
            except Exception as e:
                LOGGER.error(f"Unexpected error getting playback state: {e}")
                return []
        return []

    def clear_playback_state(self, shard_id: int):
        """복원 완료 후 재생 상태를 삭제합니다."""
        if not self.available:
            return

        client = self.get_client()
        if client:
            try:
                key = f"{self.playback_state_key_prefix}{shard_id}"
                client.delete(key)
                LOGGER.debug(f"Cleared playback state for shard {shard_id}")
            except redis.exceptions.RedisError as e:
                LOGGER.error(f"Failed to clear playback state in Redis: {e}")
            except Exception as e:
                LOGGER.error(f"Unexpected error clearing playback state: {e}")

    # --- Uptime 모니터링 (비트맵) ---

    UPTIME_CHECK_PREFIX = "uptime:checks:"
    UPTIME_COUNT_PREFIX = "uptime:check_count:"
    UPTIME_AGGREGATED_PREFIX = "uptime:aggregated:"
    UPTIME_TTL = 60 * 60 * 48  # 2일

    def record_uptime_check(self, service: str, date_str: str, check_index: int, is_up: bool):
        """업타임 체크 결과를 Redis 비트맵에 기록합니다."""
        if not self.available:
            return

        client = self.get_client()
        if client:
            try:
                bitmap_key = f"{self.UPTIME_CHECK_PREFIX}{service}:{date_str}"
                count_key = f"{self.UPTIME_COUNT_PREFIX}{service}:{date_str}"

                if is_up:
                    client.setbit(bitmap_key, check_index, 1)
                else:
                    client.setbit(bitmap_key, check_index, 0)

                # 체크 카운트 증가
                client.incr(count_key)

                # TTL 설정 (키가 새로 생성된 경우)
                if client.ttl(bitmap_key) < 0:
                    client.expire(bitmap_key, self.UPTIME_TTL)
                if client.ttl(count_key) < 0:
                    client.expire(count_key, self.UPTIME_TTL)
            except Exception as e:
                LOGGER.error(f"Failed to record uptime check: {e}")

    def get_uptime_summary(self, service: str, date_str: str) -> dict:
        """특정 날짜의 업타임 요약을 반환합니다."""
        if not self.available:
            return {"up_checks": 0, "total_checks": 0}

        client = self.get_client()
        if client:
            try:
                bitmap_key = f"{self.UPTIME_CHECK_PREFIX}{service}:{date_str}"
                count_key = f"{self.UPTIME_COUNT_PREFIX}{service}:{date_str}"

                up_checks = client.bitcount(bitmap_key)
                total_checks = client.get(count_key)
                total_checks = int(total_checks) if total_checks else 0

                return {"up_checks": up_checks, "total_checks": total_checks}
            except Exception as e:
                LOGGER.error(f"Failed to get uptime summary: {e}")
        return {"up_checks": 0, "total_checks": 0}

    def is_uptime_aggregated(self, date_str: str) -> bool:
        """해당 날짜의 업타임이 이미 집계되었는지 확인합니다."""
        if not self.available:
            return True

        client = self.get_client()
        if client:
            try:
                return bool(client.get(f"{self.UPTIME_AGGREGATED_PREFIX}{date_str}"))
            except Exception:
                return True
        return True

    def mark_uptime_aggregated(self, date_str: str):
        """해당 날짜의 업타임 집계 완료를 표시합니다."""
        if not self.available:
            return

        client = self.get_client()
        if client:
            try:
                client.set(
                    f"{self.UPTIME_AGGREGATED_PREFIX}{date_str}", "1",
                    ex=60 * 60 * 72  # 3일
                )
            except Exception as e:
                LOGGER.error(f"Failed to mark uptime aggregated: {e}")

    # --- Async Pub/Sub (웹 대시보드 양방향 통신) ---

    def get_async_client(self):
        """비동기 Redis 클라이언트를 반환합니다."""
        if not self.available:
            return None
        if not self._async_client:
            self._async_client = aioredis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                decode_responses=True,
            )
        return self._async_client

    async def publish(self, channel: str, message: str):
        """Redis 채널에 메시지를 발행합니다."""
        client = self.get_async_client()
        if client:
            try:
                await client.publish(channel, message)
            except Exception as e:
                LOGGER.error(f"Failed to publish to {channel}: {e}")

    async def publish_player_update(self, guild_id: int, event: str, state: dict):
        """플레이어 상태 변경을 웹 대시보드에 발행합니다."""
        message = json.dumps(
            {
                "guild_id": str(guild_id),
                "event": event,
                "state": state,
            }
        )
        await self.publish("bot:player_update", message)

    def create_async_pubsub(self):
        """비동기 Pub/Sub 인스턴스를 생성합니다."""
        client = self.get_async_client()
        if client:
            return client.pubsub()
        return None


# 전역 Redis 매니저 인스턴스 생성
redis_manager = RedisManager()
