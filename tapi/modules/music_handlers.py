import re
import traceback
from datetime import datetime
import pytz
import yt_dlp

import discord
import lavalink
from lavalink.events import TrackStartEvent, QueueEndEvent, TrackExceptionEvent

from tapi import (
    LOGGER,
    THEME_COLOR,
    APP_NAME_TAG_VER,
)
from tapi.utils.language import get_lan
from tapi.utils.database import Database
from tapi.utils.embed import create_standard_embed
from tapi.modules.music_views import MusicControlView


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

    async def _send_vote_message(
        self, guild_id: int, channel_id: int, user_id: int = None
    ):
        """투표 안내 메시지 전송 (다국어 지원)"""
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return

            channel = guild.get_channel(channel_id)
            if not channel:
                return

            # 길드 기반 언어 설정 사용
            embed = discord.Embed(
                title=get_lan(guild_id, "vote_title"),
                description=get_lan(guild_id, "vote_description"),
                color=THEME_COLOR,
            )
            embed.set_image(
                url="https://github.com/user-attachments/assets/8a4b3cac-8f21-42dc-9ba8-7ee0a89ece95"
            )

            # 투표/리뷰 링크 버튼 생성
            view = discord.ui.View()
            view.add_item(
                discord.ui.Button(
                    label="🌟 Top.gg Vote",
                    url="https://top.gg/bot/1157593204682657933/vote",
                    style=discord.ButtonStyle.link,
                )
            )
            view.add_item(
                discord.ui.Button(
                    label="💬 Top.gg Reviews",
                    url="https://top.gg/bot/1157593204682657933#reviews",
                    style=discord.ButtonStyle.link,
                )
            )
            view.add_item(
                discord.ui.Button(
                    label="🇰🇷 KoreanBots",
                    url="https://koreanbots.dev/bots/1157593204682657933/vote",
                    style=discord.ButtonStyle.link,
                )
            )

            await channel.send(embed=embed, view=view)
            LOGGER.debug(f"Vote message sent to guild {guild_id}")
        except Exception as e:
            LOGGER.error(f"Error sending vote message to guild {guild_id}: {e}")

    async def _full_disconnect_cleanup(
        self,
        guild_id: int,
        reason: str = "disconnect",
        send_vote: bool = False,
        channel_id: int = None,
        user_id: int = None,
    ):
        """완전한 연결 해제 정리 (메시지 + 플레이어 + 음성 연결 + 투표 안내)"""
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

        # 4. 투표 안내 메시지 (필요시)
        if send_vote and channel_id:
            await self._send_vote_message(guild_id, channel_id, user_id)

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

            # created_at을 한국 시간대로 설정
            created_at = now.strftime("%Y-%m-%d %H:%M:%S")

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
                created_at=created_at,
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
                        # TAPI 스타일의 embed 생성
                        embed = create_standard_embed(guild_id, "music_permission_dm_title", "music_permission_dm_description")
                        
                        # description에 실제 값 적용
                        description = get_lan(guild_id, "music_permission_dm_description").format(
                            track_title=track.title,
                            guild_name=guild.name,
                            channel_name=channel.name
                        )
                        embed.description = description
                        
                        await requester.send(embed=embed)
                except:
                    pass
                return


            # 이전 음악 메시지 정리
            await self._cleanup_music_message(guild_id, "new_track")

            # 음악 컨트롤 버튼 생성
            control_view = MusicControlView(self.music_cog, guild_id)

            # 일관된 embed 생성 (가짜 interaction 객체 생성)
            class FakeInteraction:
                def __init__(self, user_id, guild_id):
                    self.user = type("obj", (object,), {"id": user_id})()
                    self.guild = type("obj", (object,), {"id": guild_id})()

            fake_interaction = FakeInteraction(requester_id, guild_id)
            embed = control_view.update_embed_and_buttons(fake_interaction, player)

            if embed:
                try:
                    # 새 음악 메시지를 보내고 저장
                    message = await channel.send(embed=embed, view=control_view)
                    self.music_cog.last_music_messages[guild_id] = message
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
        channel_id = event.player.fetch("channel")

        # 모듈화된 완전 정리 함수 사용 (큐 종료 시에는 플레이어 정리 생략)
        await self._cleanup_music_message(guild_id, "queue_end")

        # Check if the voice client exists and if the player is connected
        if guild and guild.voice_client and event.player.is_connected:
            try:
                await guild.voice_client.disconnect(force=True)

                # 투표 안내 메시지 전송 (마지막 트랙의 요청자 언어 사용)
                if channel_id:
                    # 마지막 트랙 정보에서 요청자 ID 가져오기 (가능한 경우)
                    last_requester = getattr(event.player, "current", None)
                    user_id = last_requester.requester if last_requester else None
                    await self._send_vote_message(guild_id, channel_id, user_id)
            except Exception as e:
                LOGGER.error(f"Error disconnecting voice client: {e}")

    @lavalink.listener(TrackExceptionEvent)
    async def on_track_exception(self, event: TrackExceptionEvent):
        original_track_uri = event.track.uri
        original_track_title = event.track.title
        player = event.player
        requester = event.track.requester

        # The existing conditional block, with corrections
        if (
            "youtube.com/watch" in original_track_uri
            and event.severity
            in [
                "SUSPICIOUS",
                "COMMON",
                "FAULT",
            ]
            and (
                "unavailable" in event.message.lower()
                or "copyright" in event.message.lower()
                or "playback on other websites has been disabled"
                in event.message.lower()
                or "requires payment" in event.message.lower()
            )
        ):

            LOGGER.info(
                f"Attempting yt-dlp fallback for failed track: {original_track_uri}"
            )
            try:
                ydl_opts = {
                    "format": "bestaudio/best",
                    "noplaylist": True,
                    "quiet": True,
                    "no_warnings": True,
                    "skip_download": True,
                    "source_address": "0.0.0.0",
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(original_track_uri, download=False)

                stream_url_from_yt_dlp = None
                if info and "url" in info:
                    stream_url_from_yt_dlp = info["url"]
                elif info and info.get("entries") and info["entries"][0].get("url"):
                    stream_url_from_yt_dlp = info["entries"][0]["url"]

                if stream_url_from_yt_dlp:
                    LOGGER.info(
                        f"yt-dlp provided stream URL for '{original_track_title}': {stream_url_from_yt_dlp}"
                    )
                    new_results = await player.node.get_tracks(stream_url_from_yt_dlp)
                    if new_results and new_results.tracks:
                        new_track = new_results.tracks[0]
                        new_track.requester = requester

                        # Add to front of queue. If player stopped due to exception, this should play next.
                        player.add(track=new_track, requester=requester, index=0)
                        LOGGER.info(
                            f"Added yt-dlp fallback track '{new_track.title}' to front of queue for guild {player.guild_id}."
                        )

                        # If player is not playing (e.g., exception stopped it and didn't auto-play next)
                        if (
                            not player.is_playing
                            and not player.paused
                            and player.is_connected
                        ):
                            await player.play()
                        return
                    else:
                        LOGGER.warning(
                            f"yt-dlp got a stream URL, but Lavalink couldn't load it as a track: {stream_url_from_yt_dlp}"
                        )
                else:
                    LOGGER.warning(
                        f"yt-dlp did not find a streamable URL for: {original_track_uri}"
                    )

            except Exception as e:
                LOGGER.error(
                    f"yt-dlp fallback in on_track_exception failed for '{original_track_uri}': {e}"
                )

        # If fallback was not attempted or failed, send a message to the user
        channel_id = player.fetch("channel")
        if channel_id:
            channel = self.bot.get_channel(int(channel_id))
            if channel:
                embed = discord.Embed(
                    title=get_lan(
                        requester or self.bot.user.id, "music_play_fail_title"
                    ),
                    description=get_lan(
                        requester or self.bot.user.id, "music_play_fail_description"
                    ).format(
                        track_title=original_track_title,
                        error_message=event.message,
                    ),
                    color=THEME_COLOR,
                )
                embed.set_footer(text=APP_NAME_TAG_VER)
                try:
                    await channel.send(embed=embed)
                except discord.HTTPException as e:
                    LOGGER.error(
                        f"Failed to send track exception message to channel {channel_id}: {e}"
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
                    # 플레이어에서 채널 ID 가져오기
                    player = self.bot.lavalink.player_manager.get(guild.id)
                    channel_id = player.fetch("channel") if player else None

                    # 모듈화된 완전 정리 함수 사용 (투표 안내 포함)
                    await self._full_disconnect_cleanup(
                        guild.id,
                        "auto_disconnect",
                        send_vote=True,
                        channel_id=channel_id,
                    )

                    # 다국어 지원 로그 메시지 (기본값으로 한국어 사용)
                    log_message = get_lan(
                        self.bot.user.id, "music_auto_disconnect_log"
                    ).format(guild_name=guild.name)
                    LOGGER.info(log_message)

                except Exception as e:
                    error_message = get_lan(
                        self.bot.user.id, "music_auto_disconnect_error"
                    ).format(error=str(e))
                    LOGGER.error(error_message)
