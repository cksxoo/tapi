import json
import os
from tapi.sample_config import Config
from tapi import LOGGER

try:
    import redis

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
        self.shard_stats_key_prefix = "shard_stats:"
        self.active_players_key_prefix = "active_players:"
        self.shard_status_ttl = 60 * 10  # 10분
        self.active_player_ttl = 60  # 1분 (자주 업데이트되므로 짧게)
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


# 전역 Redis 매니저 인스턴스 생성
redis_manager = RedisManager()
