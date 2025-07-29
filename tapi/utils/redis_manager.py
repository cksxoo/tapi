import redis
import json
import os
from tapi.sample_config import Config
from tapi import LOGGER

class RedisManager:
    def __init__(self):
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = 6379
        self.redis_db = 0
        self.redis_client = None
        self.shard_stats_key = "shard_stats"

    def connect(self):
        """Redis 서버에 연결합니다."""
        try:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                decode_responses=True  # 응답을 자동으로 UTF-8로 디코딩
            )
            self.redis_client.ping()
            LOGGER.info("Successfully connected to Redis.")
        except redis.exceptions.ConnectionError as e:
            LOGGER.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None

    def get_client(self):
        """Redis 클라이언트 인스턴스를 반환합니다."""
        if not self.redis_client:
            self.connect()
        return self.redis_client

    def update_shard_status(self, shard_id: int, data: dict):
        """특정 샤드의 상태 정보를 업데이트합니다."""
        client = self.get_client()
        if client:
            try:
                client.hset(self.shard_stats_key, str(shard_id), json.dumps(data))
            except redis.exceptions.RedisError as e:
                LOGGER.error(f"Failed to update shard status in Redis: {e}")

    def get_all_shard_statuses(self) -> dict:
        """모든 샤드의 상태 정보를 가져옵니다."""
        client = self.get_client()
        if client:
            try:
                raw_data = client.hgetall(self.shard_stats_key)
                return {int(shard_id): json.loads(data) for shard_id, data in raw_data.items()}
            except redis.exceptions.RedisError as e:
                LOGGER.error(f"Failed to get all shard statuses from Redis: {e}")
                return {}
        return {}

# 전역 Redis 매니저 인스턴스 생성
redis_manager = RedisManager()
