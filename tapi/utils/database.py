import os
import asyncio
from datetime import datetime
import logging
from functools import lru_cache
import time
import pytz

# Supabase 클라이언트
try:
    from supabase import create_client, Client

    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logging.warning("Supabase client not installed. Run: pip install supabase")

from tapi import LOGGER


class Database:
    """Supabase 데이터베이스 핸들러"""

    _instance = None
    _client = None
    _cache = {}  # 간단한 인메모리 캐시
    _cache_ttl = 60  # 캐시 TTL (초)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """싱글톤 패턴으로 한 번만 초기화"""
        if not hasattr(self, "initialized"):
            self.initialize()
            self.initialized = True
            self.stats_buffer = []  # 통계 배치 처리용
            self.last_flush = time.time()
            self.buffer_size = 50
            self.flush_interval = 30  # 30초마다 플러시

    def initialize(self):
        """Supabase 클라이언트 초기화"""
        if not SUPABASE_AVAILABLE:
            LOGGER.error("Supabase client not available")
            return False

        # config.py에서 먼저 가져오고, 없으면 환경변수 사용
        try:
            from tapi.config import Development as Config

            url = getattr(Config, "SUPABASE_URL", None)
            key = getattr(Config, "SUPABASE_ANON_KEY", None)
        except ImportError:
            url = None
            key = None

        # config.py에 없으면 환경변수 사용
        if not url or not key:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_ANON_KEY")

        if not url or not key:
            LOGGER.error(
                "Supabase credentials not found in config.py or environment variables"
            )
            return False

        try:
            self._client = create_client(url, key)
            LOGGER.info("Successfully connected to Supabase")
            return True
        except Exception as e:
            LOGGER.error(f"Failed to connect to Supabase: {e}")
            return False

    def get_client(self):
        """클라이언트 인스턴스 반환"""
        if not self._client:
            self.initialize()
        return self._client

    def _get_cache_key(self, table, key):
        """캐시 키 생성"""
        return f"{table}:{key}"

    def _get_from_cache(self, table, key):
        """캐시에서 데이터 조회"""
        cache_key = self._get_cache_key(table, key)
        if cache_key in self._cache:
            data, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                return data
            else:
                del self._cache[cache_key]
        return None

    def _set_cache(self, table, key, data):
        """캐시에 데이터 저장"""
        cache_key = self._get_cache_key(table, key)
        self._cache[cache_key] = (data, time.time())

    def _clear_cache(self, table=None, key=None):
        """캐시 클리어"""
        if table and key:
            cache_key = self._get_cache_key(table, key)
            self._cache.pop(cache_key, None)
        elif table:
            # 특정 테이블의 모든 캐시 클리어
            keys_to_remove = [
                k for k in self._cache.keys() if k.startswith(f"{table}:")
            ]
            for k in keys_to_remove:
                del self._cache[k]
        else:
            # 전체 캐시 클리어
            self._cache.clear()

    # ===== 길드 설정 관련 메서드 =====

    def get_volume(self, guild_id):
        """길드 볼륨 설정 가져오기"""
        settings = self.get_guild_settings(guild_id)
        return settings.get("volume", 20)

    def set_volume(self, guild_id, volume):
        """길드 볼륨 설정"""
        self.upsert_guild_settings(guild_id, volume=volume)

    def get_loop(self, guild_id):
        """길드 루프 설정 가져오기"""
        settings = self.get_guild_settings(guild_id)
        return settings.get("loop_mode", 0)

    def set_loop(self, guild_id, loop_mode):
        """길드 루프 설정"""
        self.upsert_guild_settings(guild_id, loop_mode=loop_mode)

    def get_shuffle(self, guild_id):
        """길드 셔플 설정 가져오기"""
        settings = self.get_guild_settings(guild_id)
        return settings.get("shuffle", False)

    def set_shuffle(self, guild_id, shuffle):
        """길드 셔플 설정"""
        self.upsert_guild_settings(guild_id, shuffle=shuffle)

    def get_guild_settings(self, guild_id):
        """길드 설정 통합 조회 (캐시 활용)"""
        # 캐시 확인
        cached = self._get_from_cache("guild_settings", guild_id)
        if cached:
            return cached

        client = self.get_client()
        if not client:
            return {
                "guild_id": guild_id,
                "volume": 20,
                "loop_mode": 0,
                "shuffle": False,
                "language": "ko",
            }

        try:
            response = (
                client.table("guild_settings")
                .select("*")
                .eq("guild_id", str(guild_id))
                .maybe_single()
                .execute()
            )

            if response and response.data:
                self._set_cache('guild_settings', guild_id, response.data)
                return response.data
            else:
                # 기본값
                default_settings = {
                    "guild_id": guild_id,
                    "volume": 20,
                    "loop_mode": 0,
                    "shuffle": False,
                    "language": "ko",
                }
                return default_settings

        except Exception as e:
            LOGGER.error(f"Error getting guild settings: {e}")
            return {
                "guild_id": guild_id,
                "volume": 20,
                "loop_mode": 0,
                "shuffle": False,
                "language": "ko",
            }

    def upsert_guild_settings(self, guild_id, **kwargs):
        """길드 설정 UPSERT"""
        client = self.get_client()
        if not client:
            return {}

        try:
            data = {"guild_id": str(guild_id)}
            data.update(kwargs)
            # updated_at은 트리거에서 자동 설정되지만 명시적으로 설정
            if "updated_at" not in data:
                tz = pytz.timezone('Asia/Seoul')
                data["updated_at"] = datetime.now(tz).isoformat()

            response = client.table("guild_settings").upsert(data).execute()

            # 캐시 무효화
            self._clear_cache("guild_settings", guild_id)

            return response.data[0] if response.data else {}

        except Exception as e:
            LOGGER.error(f"Error upserting guild settings: {e}")
            return {}

    # ===== 길드 언어 설정 관련 메서드 =====

    def get_guild_language(self, guild_id):
        """길드 기본 언어 설정 가져오기"""
        settings = self.get_guild_settings(guild_id)
        return settings.get("language", "ko")

    def set_guild_language(self, guild_id, language):
        """길드 기본 언어 설정"""
        self.upsert_guild_settings(guild_id, language=language)

    # ===== 통계 관련 메서드 =====

    def set_statistics(
        self,
        date,
        time_str,
        guild_id,
        guild_name,
        channel_id,
        channel_name,
        user_id,
        user_name,
        video_id,
        title,
        artist,
        duration,
        success,
        created_at=None,
    ):
        """통계 저장 (배치 처리)"""
        stats_data = {
            "date": date,
            "time": time_str,
            "guild_id": str(guild_id),
            "guild_name": guild_name,
            "channel_id": str(channel_id) if channel_id else None,
            "channel_name": channel_name,
            "user_id": str(user_id),
            "user_name": user_name,
            "video_id": video_id,
            "title": title,
            "artist": artist,
            "duration": duration,
            "success": success,
            "created_at": created_at or datetime.now().isoformat(),
        }

        # 버퍼에 추가
        self.stats_buffer.append(stats_data)

        # 버퍼가 가득 찼거나 시간이 지났으면 플러시
        if (
            len(self.stats_buffer) >= self.buffer_size
            or time.time() - self.last_flush > self.flush_interval
        ):
            self.flush_statistics()

    def flush_statistics(self):
        """통계 버퍼 플러시 (배치 인서트)"""
        if not self.stats_buffer:
            return

        client = self.get_client()
        if not client:
            self.stats_buffer = []  # 연결 실패시 버퍼 클리어
            return

        try:
            # Supabase는 한 번에 대량 삽입 가능
            response = client.table("statistics").insert(self.stats_buffer).execute()

            LOGGER.debug(f"Flushed {len(self.stats_buffer)} statistics to Supabase")
            self.stats_buffer = []
            self.last_flush = time.time()

        except Exception as e:
            LOGGER.error(f"Error flushing statistics: {e}")
            # 실패한 데이터는 버퍼에 유지 (재시도를 위해)
            if len(self.stats_buffer) > 1000:  # 버퍼 오버플로우 방지
                self.stats_buffer = self.stats_buffer[-500:]

    def create_table(self):
        """테이블 생성 (Supabase에서는 SQL Editor에서 직접 실행)"""
        LOGGER.info("Tables should be created directly in Supabase SQL Editor")
        pass

    def __del__(self):
        """소멸자에서 남은 통계 플러시"""
        if hasattr(self, "stats_buffer") and self.stats_buffer:
            self.flush_statistics()
