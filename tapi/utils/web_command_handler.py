"""웹 대시보드에서 전달된 명령을 처리합니다."""

from tapi import LOGGER
from tapi.utils.database import Database
from tapi.utils.embed import get_track_thumbnail


def validate_user_in_voice(bot, guild_id: int, user_id: int):
    """사용자가 봇과 같은 음성 채널에 있는지 검증합니다."""
    guild = bot.get_guild(guild_id)
    if not guild:
        return False, "Guild not found"

    player = bot.lavalink.player_manager.get(guild_id)
    if not player or not player.is_connected:
        return False, "Bot is not connected to a voice channel"

    voice_client = guild.voice_client
    if not voice_client or not voice_client.channel:
        return False, "Bot is not in a voice channel"

    for member in voice_client.channel.members:
        if member.id == user_id:
            return True, "OK"

    return False, "You must be in the same voice channel as the bot"


def get_player_state(bot, guild_id: int) -> dict:
    """현재 플레이어 상태를 dict로 반환합니다."""
    guild = bot.get_guild(guild_id)
    player = bot.lavalink.player_manager.get(guild_id)

    if not player:
        LOGGER.debug(f"get_player_state({guild_id}): no player found")
        return {"guild_id": str(guild_id), "is_connected": False, "is_playing": False, "current_track": None, "queue": [], "queue_length": 0}

    current_track = None
    if player.current:
        current_track = {
            "title": player.current.title,
            "author": player.current.author,
            "uri": player.current.uri,
            "duration": player.current.duration,
            "position": player.position,
            "thumbnail": get_track_thumbnail(player.current),
        }

    queue = []
    for track in player.queue:
        queue.append({
            "title": track.title,
            "author": track.author,
            "uri": track.uri,
            "duration": track.duration,
            "thumbnail": get_track_thumbnail(track),
        })

    channel_name = "Unknown"
    if guild and guild.voice_client and guild.voice_client.channel:
        channel_name = guild.voice_client.channel.name

    return {
        "guild_id": str(guild_id),
        "is_connected": player.is_connected,
        "is_playing": player.is_playing,
        "is_paused": player.paused,
        "current_track": current_track,
        "queue": queue,
        "queue_length": len(player.queue),
        "volume": player.volume,
        "loop": player.loop,
        "shuffle": player.shuffle,
        "channel_name": channel_name,
    }


async def handle_pause(bot, guild_id: int, user_id: int, **_params):
    valid, msg = validate_user_in_voice(bot, guild_id, user_id)
    if not valid:
        return {"success": False, "error": msg}

    player = bot.lavalink.player_manager.get(guild_id)
    await player.set_pause(not player.paused)
    return {"success": True, "data": {"paused": player.paused}}


async def handle_skip(bot, guild_id: int, user_id: int, **_params):
    valid, msg = validate_user_in_voice(bot, guild_id, user_id)
    if not valid:
        return {"success": False, "error": msg}

    player = bot.lavalink.player_manager.get(guild_id)
    if player.loop == 1:
        player.set_loop(2)
        Database().set_loop(guild_id, 2)
    await player.skip()
    return {"success": True}


async def handle_stop(bot, guild_id: int, user_id: int, **_params):
    valid, msg = validate_user_in_voice(bot, guild_id, user_id)
    if not valid:
        return {"success": False, "error": msg}

    guild = bot.get_guild(guild_id)
    if guild and guild.voice_client:
        player = bot.lavalink.player_manager.get(guild_id)
        player.queue.clear()
        await player.stop()
        await guild.voice_client.disconnect(force=True)
    return {"success": True}


async def handle_volume(bot, guild_id: int, user_id: int, volume: int = 50, **_params):
    valid, msg = validate_user_in_voice(bot, guild_id, user_id)
    if not valid:
        return {"success": False, "error": msg}

    player = bot.lavalink.player_manager.get(guild_id)
    volume = max(0, min(100, volume))
    await player.set_volume(volume)
    Database().set_volume(guild_id, volume)
    return {"success": True, "data": {"volume": volume}}


async def handle_repeat(bot, guild_id: int, user_id: int, **_params):
    valid, msg = validate_user_in_voice(bot, guild_id, user_id)
    if not valid:
        return {"success": False, "error": msg}

    player = bot.lavalink.player_manager.get(guild_id)
    new_loop = (player.loop + 1) % 3
    player.set_loop(new_loop)
    Database().set_loop(guild_id, new_loop)
    return {"success": True, "data": {"loop": new_loop}}


async def handle_shuffle(bot, guild_id: int, user_id: int, **_params):
    valid, msg = validate_user_in_voice(bot, guild_id, user_id)
    if not valid:
        return {"success": False, "error": msg}

    player = bot.lavalink.player_manager.get(guild_id)
    player.set_shuffle(not player.shuffle)
    Database().set_shuffle(guild_id, player.shuffle)
    return {"success": True, "data": {"shuffle": player.shuffle}}


async def handle_search(bot, guild_id: int, user_id: int, query: str = "", **_params):
    valid, msg = validate_user_in_voice(bot, guild_id, user_id)
    if not valid:
        return {"success": False, "error": msg}

    player = bot.lavalink.player_manager.get(guild_id)
    if not query:
        return {"success": False, "error": "No query provided"}

    results = await player.node.get_tracks(f"ytsearch:{query}")
    if not results or not results.tracks:
        return {"success": False, "error": "No results found"}

    tracks = []
    for track in results.tracks[:10]:
        tracks.append({
            "title": track.title,
            "author": track.author,
            "uri": track.uri,
            "duration": track.duration,
            "identifier": track.identifier,
        })

    return {"success": True, "data": {"tracks": tracks}}


async def handle_play(bot, guild_id: int, user_id: int, query: str = "", **_params):
    valid, msg = validate_user_in_voice(bot, guild_id, user_id)
    if not valid:
        return {"success": False, "error": msg}

    player = bot.lavalink.player_manager.get(guild_id)
    if not query:
        return {"success": False, "error": "No query provided"}

    # 텍스트 채널이 설정되지 않은 경우 (웹에서 첫 재생 시) 자동 설정
    if not player.fetch("channel"):
        guild = bot.get_guild(guild_id)
        if guild:
            text_channel = None
            # 시스템 채널 (권한 있을 때만)
            if guild.system_channel:
                perms = guild.system_channel.permissions_for(guild.me)
                if perms.send_messages:
                    text_channel = guild.system_channel
            # 없으면 권한 있는 첫 번째 텍스트 채널
            if not text_channel:
                for ch in guild.text_channels:
                    perms = ch.permissions_for(guild.me)
                    if perms.send_messages:
                        text_channel = ch
                        break
            if text_channel:
                player.store("channel", text_channel.id)

    # URL이면 직접 검색, 아니면 ytsearch 추가
    if not query.startswith("http"):
        query = f"ytsearch:{query}"

    results = await player.node.get_tracks(query)
    if not results or not results.tracks:
        return {"success": False, "error": "No results found"}

    track = results.tracks[0]
    player.add(requester=user_id, track=track)

    if not player.is_playing:
        await player.play()

    return {"success": True, "data": {
        "title": track.title,
        "author": track.author,
        "uri": track.uri,
    }}


async def handle_remove(bot, guild_id: int, user_id: int, index: int = 0, **_params):
    valid, msg = validate_user_in_voice(bot, guild_id, user_id)
    if not valid:
        return {"success": False, "error": msg}

    player = bot.lavalink.player_manager.get(guild_id)
    if index < 0 or index >= len(player.queue):
        return {"success": False, "error": "Invalid queue index"}

    removed = player.queue.pop(index)
    return {"success": True, "data": {"removed": removed.title}}


async def handle_move(bot, guild_id: int, user_id: int, from_index: int = 0, to_index: int = 0, **_params):
    valid, msg = validate_user_in_voice(bot, guild_id, user_id)
    if not valid:
        return {"success": False, "error": msg}

    player = bot.lavalink.player_manager.get(guild_id)
    if from_index < 0 or from_index >= len(player.queue):
        return {"success": False, "error": "Invalid source index"}
    if to_index < 0 or to_index >= len(player.queue):
        return {"success": False, "error": "Invalid target index"}
    if from_index == to_index:
        return {"success": True}

    track = player.queue.pop(from_index)
    player.queue.insert(to_index, track)
    return {"success": True}


async def handle_seek(bot, guild_id: int, user_id: int, position: int = 0, **_params):
    valid, msg = validate_user_in_voice(bot, guild_id, user_id)
    if not valid:
        return {"success": False, "error": msg}

    player = bot.lavalink.player_manager.get(guild_id)
    if not player.current:
        return {"success": False, "error": "No track playing"}

    position = max(0, min(int(position), player.current.duration))
    await player.seek(position)
    return {"success": True, "data": {"position": position}}


async def handle_get_state(bot, guild_id: int, user_id: int, **_params):
    """플레이어 상태를 반환합니다 (voice 검증 불필요)."""
    state = get_player_state(bot, guild_id)
    return {"success": True, "data": state}


# 명령 디스패처
COMMAND_HANDLERS = {
    "get_state": handle_get_state,
    "pause": handle_pause,
    "skip": handle_skip,
    "stop": handle_stop,
    "volume": handle_volume,
    "repeat": handle_repeat,
    "shuffle": handle_shuffle,
    "search": handle_search,
    "play": handle_play,
    "remove": handle_remove,
    "move": handle_move,
    "seek": handle_seek,
}


async def dispatch_command(bot, command: str, guild_id: int, user_id: int, params: dict) -> dict:
    """명령을 적절한 핸들러로 디스패치합니다."""
    handler = COMMAND_HANDLERS.get(command)
    if not handler:
        return {"success": False, "error": f"Unknown command: {command}"}

    try:
        return await handler(bot, guild_id, user_id, **params)
    except Exception as e:
        LOGGER.error(f"Error handling web command '{command}': {e}")
        return {"success": False, "error": str(e)}
