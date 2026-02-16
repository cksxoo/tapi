"""Redis Pub/Sub 리스너 - 웹 대시보드 명령 수신 처리"""

import json
import asyncio
from tapi import LOGGER
from tapi.utils.redis_manager import redis_manager
from tapi.utils.web_command_handler import dispatch_command, get_player_state


async def start_command_listener(bot):
    """웹 대시보드 명령을 수신하는 백그라운드 태스크를 시작합니다."""
    if not redis_manager.available:
        LOGGER.warning("Redis not available, web command listener disabled")
        return

    await bot.wait_until_ready()
    LOGGER.info("Starting web command listener...")

    while True:
        try:
            await _listen_for_commands(bot)
        except asyncio.CancelledError:
            LOGGER.info("Web command listener cancelled")
            break
        except Exception as e:
            LOGGER.error(f"Web command listener error: {e}")
            await asyncio.sleep(5)  # 재연결 대기


async def _listen_for_commands(bot):
    """Redis Pub/Sub에서 명령을 수신하고 처리합니다."""
    pubsub = redis_manager.create_async_pubsub()
    if not pubsub:
        LOGGER.error("Failed to create async pubsub")
        return

    await pubsub.subscribe("bot:command")
    LOGGER.info("Subscribed to bot:command channel")

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue

            try:
                data = json.loads(message["data"])
                await _process_command(bot, data)
            except json.JSONDecodeError:
                LOGGER.error(f"Invalid JSON in command: {message['data']}")
            except Exception as e:
                LOGGER.error(f"Error processing command: {e}")
    finally:
        await pubsub.unsubscribe("bot:command")
        await pubsub.close()


async def _process_command(bot, data: dict):
    """수신된 명령을 처리합니다."""
    guild_id = int(data.get("guild_id", 0))
    request_id = data.get("request_id", "")
    command = data.get("command", "")
    user_id = int(data.get("user_id", 0))
    params = data.get("params", {})

    # 이 샤드가 해당 길드를 관리하는지 확인
    guild = bot.get_guild(guild_id)
    if not guild:
        return  # 다른 샤드가 처리

    LOGGER.info(f"Web command: {command} for guild {guild_id} by user {user_id}")

    # 명령 실행
    result = await dispatch_command(bot, command, guild_id, user_id, params)

    # 응답 발행
    response_channel = f"bot:response:{request_id}"
    await redis_manager.publish(response_channel, json.dumps(result))

    if not result.get("success"):
        LOGGER.info(f"Web command failed: {command} - {result.get('error', 'unknown')}")

    # 상태 변경 시 player_update 발행 (search 제외)
    if result.get("success") and command != "search":
        state = get_player_state(bot, guild_id)
        await redis_manager.publish_player_update(guild_id, command, state)

        # Discord Now Playing 메시지 동기화
        try:
            from tapi.utils.v2_components import sync_discord_message
            await sync_discord_message(bot, guild_id, command, user_id)
        except Exception as e:
            LOGGER.debug(f"Failed to sync discord message: {e}")
