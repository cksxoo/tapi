import re
import traceback
from datetime import datetime
import pytz

import discord
from discord import ui
import lavalink
from lavalink.events import TrackStartEvent, QueueEndEvent, TrackExceptionEvent

from tapi import LOGGER, THEME_COLOR
from tapi.utils.database import Database
from tapi.modules.music_views import MusicControlLayout
from tapi.utils.v2_components import (
    make_themed_container, make_separator, make_banner_gallery, FakeInteraction,
)


class MusicHandlers:
    """음악 관련 이벤트 처리 및 헬퍼 메서드들을 모아둔 클래스"""

    def __init__(self, music_cog):
        self.music_cog = music_cog
        self.bot = music_cog.bot

    async def _cleanup_music_message(self, guild_id: int, reason: str = "cleanup"):
        """음악 메시지 정리 함수"""
        if guild_id not in self.music_cog.last_music_messages:
            return

        try:
            old_message = self.music_cog.last_music_messages[guild_id]
            await old_message.delete()
            LOGGER.debug(f"Music message deleted on {reason} for guild {guild_id}")
        except Exception as e:
            LOGGER.debug(f"Could not delete music message on {reason}: {e}")
        finally:
            # 딕셔너리에서 안전하게 제거
            if guild_id in self.music_cog.last_music_messages:
                del self.music_cog.last_music_messages[guild_id]

    async def _cleanup_player(
        self, guild_id: int, stop_current: bool = True, clear_queue: bool = True
    ):
        """Lavalink 플레이어 정리 함수"""
        try:
            player = self.bot.lavalink.player_manager.get(guild_id)
            if player:
                if stop_current:
                    await player.stop()
                if clear_queue:
                    player.queue.clear()
                LOGGER.debug(f"Player cleaned up for guild {guild_id}")
        except Exception as e:
            LOGGER.error(f"Error cleaning up player for guild {guild_id}: {e}")


    async def _full_disconnect_cleanup(
        self,
        guild_id: int,
        reason: str = "disconnect",
    ):
        """완전한 연결 해제 정리 (메시지 + 플레이어 + 음성 연결)"""
        # 1. 음악 메시지 정리
        await self._cleanup_music_message(guild_id, reason)

        # 2. 플레이어 정리
        await self._cleanup_player(guild_id)

        # 3. 음성 연결 해제
        try:
            guild = self.bot.get_guild(guild_id)
            if guild and guild.voice_client:
                await guild.voice_client.disconnect(force=True)
                LOGGER.debug(f"Voice client disconnected for guild {guild_id}")
        except Exception as e:
            LOGGER.error(f"Error disconnecting voice client for guild {guild_id}: {e}")

    @lavalink.listener(TrackStartEvent)
    async def on_track_start(self, event: TrackStartEvent):
        guild_id = event.player.guild_id
        channel_id = event.player.fetch("channel")
        guild = self.bot.get_guild(guild_id)

        if not guild:
            return await self.bot.lavalink.player_manager.destroy(guild_id)

        channel = guild.get_channel(channel_id)
        player = self.bot.lavalink.player_manager.get(guild_id)
        track = event.track
        requester_id = track.requester

        # 통계 저장
        try:
            # 한국 시간대 설정
            kst = pytz.timezone("Asia/Seoul")
            now = datetime.now(kst)
            date = now.strftime("%Y-%m-%d")
            time = now.strftime("%H:%M:%S")

            # 사용자 정보 안전하게 가져오기
            user_name = "Unknown User"
            try:
                # 먼저 캐시에서 확인
                requester = self.bot.get_user(requester_id)
                if requester:
                    user_name = requester.name
                else:
                    # 캐시에 없으면 API에서 가져오기
                    requester = await self.bot.fetch_user(requester_id)
                    user_name = requester.name if requester else f"User-{requester_id}"
            except Exception as user_error:
                LOGGER.warning(f"Could not fetch user {requester_id}: {user_error}")
                user_name = f"User-{requester_id}"

            # duration을 밀리초에서 초로 변환
            duration_seconds = track.duration // 1000

            Database().set_statistics(
                date=date,
                time_str=time,
                guild_id=str(guild.id),
                guild_name=guild.name,
                channel_id=str(channel.id),
                channel_name=channel.name,
                user_id=str(requester_id),
                user_name=user_name,
                video_id=track.identifier,
                title=track.title,
                artist=track.author,
                duration=duration_seconds,
                success=True,
            )
        except Exception as e:
            LOGGER.error(f"Error saving statistics: {e}")

        if channel:
            # 채널에 메시지를 보낼 권한이 있는지 확인
            bot_member = guild.get_member(self.bot.user.id)
            permissions = channel.permissions_for(bot_member) if bot_member else None

            if not bot_member or not permissions or not permissions.send_messages:
                LOGGER.warning(
                    f"Bot lacks send_messages permission in channel {channel.id} ({channel.name}) in guild {guild.id}"
                )
                # 채널에 메시지를 못 보내니 DM으로라도 알림
                try:
                    requester = self.bot.get_user(requester_id)
                    if not requester:
                        requester = await self.bot.fetch_user(requester_id)
                    if requester:
                        dm_view = ui.LayoutView(timeout=None)
                        dm_view.add_item(make_themed_container(
                            ui.TextDisplay("## ⚠️ Permission Required"),
                            ui.TextDisplay(
                                f"I don't have permission to send messages in **{channel.name}** "
                                f"(Server: {guild.name}).\n\n"
                                f"Playing: **{track.title}**\n\n"
                                f"Please ask a server admin to grant me 'Send Messages' permission in that channel."
                            ),
                            accent_color=0xFF6600,
                        ))
                        await requester.send(view=dm_view)
                except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                    pass
                return

            # 이전 음악 메시지 정리
            await self._cleanup_music_message(guild_id, "new_track")

            # 음악 컨트롤 V2 레이아웃 생성
            control_layout = MusicControlLayout(self.music_cog, guild_id)

            # 사용자의 저장된 언어 설정 가져오기 (없으면 기본값 영어)
            user_locale = self.music_cog.user_locales.get(requester_id, 'en')
            fake_interaction = FakeInteraction(requester_id, guild_id, user_locale)
            control_layout.build_layout(fake_interaction, player)

            # 웹 대시보드에 실시간 상태 발행
            try:
                from tapi.utils.redis_manager import redis_manager
                from tapi.utils.web_command_handler import get_player_state
                state = get_player_state(self.bot, guild_id)
                await redis_manager.publish_player_update(guild_id, "track_start", state)
            except Exception as e:
                LOGGER.debug(f"Failed to publish player update: {e}")

            try:
                # 새 음악 메시지를 보내고 저장
                message = await channel.send(view=control_layout)
                self.music_cog.last_music_messages[guild_id] = message
                LOGGER.debug(f"Created new music message for guild {guild_id}")
                return message
            except discord.Forbidden:
                LOGGER.warning(
                    f"Failed to send music message in channel {channel.id} due to insufficient permissions"
                )
            except Exception as e:
                LOGGER.error(f"Error sending music message: {e}")

    @lavalink.listener(QueueEndEvent)
    async def on_queue_end(self, event: QueueEndEvent):
        guild_id = event.player.guild_id
        guild = self.bot.get_guild(guild_id)

        # 모듈화된 완전 정리 함수 사용 (큐 종료 시에는 플레이어 정리 생략)
        await self._cleanup_music_message(guild_id, "queue_end")

        # 웹 대시보드에 큐 종료 발행
        try:
            from tapi.utils.redis_manager import redis_manager
            from tapi.utils.web_command_handler import get_player_state
            state = get_player_state(self.bot, guild_id)
            await redis_manager.publish_player_update(guild_id, "queue_end", state)
        except Exception as e:
            LOGGER.debug(f"Failed to publish queue end update: {e}")

        # Check if the voice client exists and if the player is connected
        if guild and guild.voice_client and event.player.is_connected:
            try:
                await guild.voice_client.disconnect(force=True)
            except Exception as e:
                LOGGER.error(f"Error disconnecting voice client: {e}")

    @lavalink.listener(TrackExceptionEvent)
    async def on_track_exception(self, event: TrackExceptionEvent):
        original_track_uri = event.track.uri
        original_track_title = event.track.title

        # 로그만 남기고 사용자에게는 메시지를 보내지 않음
        LOGGER.warning(
            f"Track playback failed: '{original_track_title}' (URI: {original_track_uri}) - "
            f"Severity: {event.severity}, Error: {event.message}"
        )

    async def on_voice_state_update(self, member, before, after):
        """
        음성 채널에서 사용자가 모두 나갔을 때 봇을 자동으로 연결 해제하는 기능
        """
        # 봇 자신의 음성 상태 변경은 무시
        if member.bot:
            return

        # 사용자가 음성 채널에서 나간 경우만 처리
        if before.channel and not after.channel:
            guild = before.channel.guild

            # 봇이 해당 길드의 음성 채널에 연결되어 있는지 확인
            if not guild.voice_client:
                return

            # 봇이 연결된 음성 채널 확인
            bot_voice_channel = guild.voice_client.channel

            # 사용자가 나간 채널이 봇이 있는 채널과 같은지 확인
            if before.channel != bot_voice_channel:
                return

            # 음성 채널에 남아있는 사용자 수 확인 (봇 제외)
            non_bot_members = [m for m in bot_voice_channel.members if not m.bot]

            # 봇만 남아있다면 연결 해제
            if len(non_bot_members) == 0:
                try:
                    # 모듈화된 완전 정리 함수 사용
                    await self._full_disconnect_cleanup(
                        guild.id,
                        "auto_disconnect",
                    )

                    LOGGER.info(f"Auto-disconnected from voice channel in guild {guild.name}")

                except Exception as e:
                    LOGGER.error(f"Error during auto-disconnect in guild {guild.name}: {e}")
