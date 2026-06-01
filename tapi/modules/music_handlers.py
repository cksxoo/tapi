import asyncio
import re
import time
from datetime import datetime
import pytz

import discord
from discord import ui
import lavalink
from lavalink.events import TrackStartEvent, QueueEndEvent, TrackExceptionEvent

from tapi import LOGGER
from tapi.utils.database import Database
from tapi.modules.music_views import MusicControlLayout
from tapi.utils.v2_components import (
    make_themed_container,
    FakeInteraction,
)


class MusicHandlers:
    """음악 관련 이벤트 처리 및 헬퍼 메서드들을 모아둔 클래스"""

    def __init__(self, music_cog):
        self.music_cog = music_cog
        self.bot = music_cog.bot
        self._disconnect_tasks: dict[int, tuple[asyncio.Task, str]] = {}
        # guild_id -> (실패 URI, monotonic timestamp). 같은 트랙 중복 처리 방지용.
        self._last_exception: dict[int, tuple[str, float]] = {}

    async def _cleanup_music_message(self, guild_id: int, reason: str = "cleanup"):
        """음악 메시지 정리 함수"""
        if guild_id not in self.music_cog.last_music_messages:
            LOGGER.info(
                f"[msg_cleanup] no tracked message for guild {guild_id} (reason={reason})"
            )
            return

        try:
            old_message = self.music_cog.last_music_messages[guild_id]
            await old_message.delete()
            LOGGER.info(f"[msg_cleanup] deleted message on {reason} for guild {guild_id}")
        except Exception as e:
            LOGGER.info(f"[msg_cleanup] FAILED to delete on {reason} for guild {guild_id}: {e!r}")
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
        # 0. 대기 중인 지연 퇴장 타이머 취소 (QueueEndEvent 등과의 race 방지)
        self._cancel_disconnect_task(guild_id)

        # 1. 음악 메시지 정리
        await self._cleanup_music_message(guild_id, reason)

        # 2. 음성 연결 해제 (player.stop → QueueEndEvent race 방지를 위해 먼저 연결 해제)
        try:
            guild = self.bot.get_guild(guild_id)
            if guild and guild.voice_client:
                await guild.voice_client.disconnect(force=True)
                LOGGER.debug(f"Voice client disconnected for guild {guild_id}")
        except Exception as e:
            LOGGER.error(f"Error disconnecting voice client for guild {guild_id}: {e}")

        # 3. 플레이어 정리 (disconnect 후 실행하여 QueueEndEvent가 다시 disconnect 시도하지 않도록)
        await self._cleanup_player(guild_id)

    def _cancel_disconnect_task(
        self, guild_id: int, only: set[str] | None = None
    ):
        """대기 중인 지연 퇴장 타이머 취소.

        only가 지정되면 저장된 reason이 해당 집합에 포함된 경우에만 취소한다.
        (예: 유저 입장 시엔 auto_disconnect 타이머만 취소하고 queue_end 타이머는 유지)
        """
        entry = self._disconnect_tasks.get(guild_id)
        if not entry:
            return
        task, reason = entry
        if only is not None and reason not in only:
            return
        self._disconnect_tasks.pop(guild_id, None)
        if task and not task.done():
            task.cancel()
            LOGGER.debug(
                f"Cancelled delayed disconnect for guild {guild_id} (reason={reason})"
            )

    @lavalink.listener(TrackStartEvent)
    async def on_track_start(self, event: TrackStartEvent):
        guild_id = event.player.guild_id
        # 새 트랙 시작 시 대기 중인 퇴장 타이머 취소
        self._cancel_disconnect_task(guild_id)
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

            # 사용자 정보 (캐시 only — API 호출은 글로벌 레이트리밋 위험)
            requester = self.bot.get_user(requester_id)
            user_name = requester.name if requester else f"User-{requester_id}"

            # duration을 밀리초에서 초로 변환
            duration_seconds = track.duration // 1000

            Database().set_statistics(
                date=date,
                time_str=time,
                guild_id=str(guild.id),
                guild_name=guild.name,
                channel_id=str(channel.id) if channel else "web",
                channel_name=channel.name if channel else "Web Dashboard",
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
                # 채널에 메시지를 못 보내니 DM으로라도 알림 (캐시에 있을 때만)
                try:
                    requester = self.bot.get_user(requester_id)
                    if requester:
                        dm_view = ui.LayoutView(timeout=None)
                        dm_view.add_item(
                            make_themed_container(
                                ui.TextDisplay("## ⚠️ Permission Required"),
                                ui.TextDisplay(
                                    f"I don't have permission to send messages in **{channel.name}** "
                                    f"(Server: {guild.name}).\n\n"
                                    f"Playing: **{track.title}**\n\n"
                                    f"Please ask a server admin to grant me 'Send Messages' permission in that channel."
                                ),
                                accent_color=0xFF6600,
                            )
                        )
                        await requester.send(view=dm_view)
                except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                    pass
                return

            # 음악 컨트롤 V2 레이아웃 생성
            control_layout = MusicControlLayout(self.music_cog, guild_id)

            # 사용자의 저장된 언어 설정 가져오기 (없으면 기본값 영어)
            user_locale = self.music_cog.user_locales.get(requester_id, "en")
            fake_interaction = FakeInteraction(requester_id, guild_id, user_locale)
            control_layout.build_layout(fake_interaction, player)

            # 웹 대시보드에 실시간 상태 발행
            try:
                from tapi.utils.redis_manager import redis_manager
                from tapi.utils.web_command_handler import get_player_state

                state = get_player_state(self.bot, guild_id)
                await redis_manager.publish_player_update(
                    guild_id, "track_start", state
                )
            except Exception as e:
                LOGGER.debug(f"Failed to publish player update: {e}")

            # 트랙 변경 시 기존 메시지를 편집 (delete+send → edit 1건으로 API 호출 절반 감소)
            existing_message = self.music_cog.last_music_messages.get(guild_id)
            try:
                if existing_message is not None:
                    try:
                        await existing_message.edit(view=control_layout)
                        LOGGER.debug(f"Edited existing music message for guild {guild_id}")
                        return existing_message
                    except discord.NotFound:
                        # 메시지가 이미 삭제됨 → 새로 전송
                        self.music_cog.last_music_messages.pop(guild_id, None)

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

    async def _handle_queue_end(self, guild_id: int, reason: str = "queue_end"):
        """큐 종료 정리: 메시지 삭제 + redis publish + (즉시/30초 후) 퇴장 타이머.

        QueueEndEvent 자연 발생 외에도, TrackException → player.stop() 처럼
        QueueEndEvent가 안 뜨는 케이스에서도 이 함수를 직접 호출해서 같은 정리 수행.
        """
        await self._cleanup_music_message(guild_id, reason)

        # 웹 대시보드에 발행
        try:
            from tapi.utils.redis_manager import redis_manager
            from tapi.utils.web_command_handler import get_player_state

            state = get_player_state(self.bot, guild_id)
            await redis_manager.publish_player_update(guild_id, "queue_end", state)
        except Exception as e:
            LOGGER.debug(f"Failed to publish queue end update: {e}")

        guild = self.bot.get_guild(guild_id)
        if not (guild and guild.voice_client):
            return

        db = Database()
        if db.get_instant_disconnect(guild_id):
            await self._full_disconnect_cleanup(guild_id, reason)
            return

        # 30초 후 퇴장
        self._cancel_disconnect_task(guild_id)

        async def delayed_disconnect():
            try:
                await asyncio.sleep(30)
                await self._full_disconnect_cleanup(
                    guild_id, f"{reason}_delayed"
                )
                LOGGER.debug(f"Delayed disconnect for guild {guild_id}")
            except asyncio.CancelledError:
                pass
            except Exception as e:
                LOGGER.error(f"Error in delayed disconnect: {e}")
            finally:
                self._disconnect_tasks.pop(guild_id, None)

        self._disconnect_tasks[guild_id] = (
            asyncio.create_task(delayed_disconnect()),
            "queue_end",
        )

    @lavalink.listener(QueueEndEvent)
    async def on_queue_end(self, event: QueueEndEvent):
        await self._handle_queue_end(event.player.guild_id, "queue_end")

    @lavalink.listener(TrackExceptionEvent)
    async def on_track_exception(self, event: TrackExceptionEvent):
        original_track_uri = event.track.uri
        original_track_title = event.track.title
        player = event.player
        guild_id = player.guild_id

        LOGGER.warning(
            f"Track playback failed: '{original_track_title}' (URI: {original_track_uri}) - "
            f"Severity: {event.severity}, Error: {event.message}"
        )

        severity = str(event.severity).lower()
        if "suspicious" not in severity and "fault" not in severity:
            return

        # 같은 트랙이 짧은 시간 내 반복 예외 → Lavalink 서버사이드 retry. 이미 처리 중이므로 중복 무시.
        now = time.monotonic()
        last = self._last_exception.get(guild_id)
        if last and last[0] == original_track_uri and now - last[1] < 5.0:
            return
        self._last_exception[guild_id] = (original_track_uri, now)

        # skip()은 서버사이드 retry와 race가 나서 안 통함. 명시적 stop + 다음 트랙 직접 재생.
        # loop=2(queue loop) 상태에서 play(next_track)을 부르면 lavalink.py가 현재 트랙(깨진 거)을
        # 큐 끝에 자동 append → 깨진 트랙이 다시 돌아옴. 따라서 loop을 잠시 꺼서 re-add를 막는다.
        try:
            original_loop = player.loop
            if original_loop != 0:
                player.set_loop(0)

            queue_emptied = False
            try:
                if player.queue:
                    next_track = player.queue.pop(0)
                    await player.play(next_track)
                    LOGGER.debug(
                        f"Advanced past suspicious track in guild {guild_id}"
                    )
                else:
                    await player.stop()
                    queue_emptied = True
                    LOGGER.debug(
                        f"Stopped player after suspicious track in guild {guild_id} (queue empty)"
                    )
            finally:
                # queue loop만 복원. single loop(1)은 그 깨진 트랙을 반복하려던 의도였으므로
                # 복원하면 새 트랙을 무한 반복하게 됨 → 의도 X. queue loop은 깨진 트랙만 빼고 계속.
                if original_loop == 2:
                    player.set_loop(2)

            # stop()은 QueueEndEvent를 안 띄우는 경우가 있어서, 메시지/타이머 정리를 직접 호출.
            if queue_emptied:
                await self._handle_queue_end(guild_id, "exception_stop")
        except Exception as e:
            LOGGER.error(f"Failed to recover from suspicious track: {e}")

    async def on_voice_state_update(self, member, before, after):
        """
        음성 채널에서 사용자가 모두 나갔을 때 봇을 자동으로 연결 해제하는 기능
        """
        # 봇 자신의 음성 상태 변경은 무시
        if member.bot:
            return

        # 사용자가 봇이 있는 채널에 들어오거나 이동해오면 auto_disconnect 타이머만 취소
        # (queue_end 타이머는 재생할 곡이 없다는 의미이므로 유지되어야 함)
        if after.channel:
            guild = after.channel.guild
            if guild.voice_client and after.channel == guild.voice_client.channel:
                self._cancel_disconnect_task(guild.id, only={"auto_disconnect"})

        # 사용자가 음성 채널에서 나가거나 다른 채널로 이동한 경우 처리
        if not before.channel:
            return

        guild = before.channel.guild

        # 같은 채널 내 상태 변경(음소거 등)은 무시
        if after.channel == before.channel:
            return

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
            db = Database()
            if db.get_instant_disconnect(guild.id):
                # 즉시 퇴장
                try:
                    await self._full_disconnect_cleanup(
                        guild.id,
                        "auto_disconnect",
                    )
                    LOGGER.info(
                        f"Auto-disconnected from voice channel in guild {guild.name}"
                    )
                except Exception as e:
                    LOGGER.error(
                        f"Error during auto-disconnect in guild {guild.name}: {e}"
                    )
            else:
                # 30초 후 퇴장
                self._cancel_disconnect_task(guild.id)

                async def delayed_auto_disconnect(g_id, g_name):
                    try:
                        await asyncio.sleep(30)
                        await self._full_disconnect_cleanup(
                            g_id, "auto_disconnect_delayed"
                        )
                        LOGGER.info(
                            f"Delayed auto-disconnect from voice channel in guild {g_name}"
                        )
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        LOGGER.error(
                            f"Error during delayed auto-disconnect in guild {g_name}: {e}"
                        )
                    finally:
                        self._disconnect_tasks.pop(g_id, None)

                self._disconnect_tasks[guild.id] = (
                    asyncio.create_task(
                        delayed_auto_disconnect(guild.id, guild.name)
                    ),
                    "auto_disconnect",
                )

    async def handle_autoplay_message(self, message: discord.Message):
        """봇 전용 채널에 올라온 유튜브 링크를 감지하여 자동 재생.
        MESSAGE_CONTENT_INTENT 가 활성화된 경우에만 on_message 에서 호출됨.
        """
        # 봇 전용 채널 확인
        bot_channel_id = Database().get_channel(message.guild.id)
        if not bot_channel_id or message.channel.id != bot_channel_id:
            return

        # 유튜브 링크 추출
        yt_pattern = re.compile(
            r"https?://(?:www\.)?(?:youtube\.com/watch\?[^\s]*v=[\w-]+|youtu\.be/[\w-]+|youtube\.com/shorts/[\w-]+)"
        )
        urls = yt_pattern.findall(message.content)
        if not urls:
            return

        # 유저가 음성 채널에 있는지 확인
        member = message.guild.get_member(message.author.id)
        if not member or not member.voice or not member.voice.channel:
            await message.channel.send(
                f"⚠️ {message.author.mention} 먼저 음성 채널에 입장해 주세요!",
                delete_after=8,
            )
            return

        voice_channel = member.voice.channel

        if not self.bot.lavalink:
            return

        try:
            from tapi.modules.audio_connection import AudioConnection

            # 플레이어 생성 또는 가져오기
            existing_player = self.bot.lavalink.player_manager.get(message.guild.id)
            player = self.bot.lavalink.player_manager.create(message.guild.id)

            # 새 플레이어면 DB 설정 적용
            if existing_player is None:
                from tapi.modules.player import Music

                await Music._setup_player_settings(player, message.guild.id)

            # 음성 채널 연결 (아직 연결 안 된 경우)
            if not message.guild.voice_client:
                perms = voice_channel.permissions_for(message.guild.me)
                if not perms.connect or not perms.speak:
                    await message.channel.send(
                        "⚠️ 음성 채널에 접근할 권한이 없습니다.",
                        delete_after=8,
                    )
                    return
                player.store("channel", message.channel.id)
                await voice_channel.connect(cls=AudioConnection, self_deaf=True)
            elif message.guild.voice_client.channel.id != voice_channel.id:
                await message.channel.send(
                    f"⚠️ {message.author.mention} 봇이 있는 음성 채널로 입장해 주세요!",
                    delete_after=8,
                )
                return

            # 첫 번째 URL만 처리 (복수 링크 도배 방지)
            url = urls[0]
            query, _ = self.music_cog._prepare_query(url)
            results = await self.music_cog._search_tracks(player, query, url, False)

            if not results:
                await message.channel.send(
                    f"⚠️ `{url}` 에서 재생 가능한 트랙을 찾을 수 없습니다.",
                    delete_after=8,
                )
                return

            added, total = await self.music_cog._add_tracks_to_player(
                player, results, message.author.id
            )

            if added == 0:
                await message.channel.send(
                    "⚠️ 대기열이 가득 찼습니다.",
                    delete_after=8,
                )
                return

            # 재생 시작
            if not player.is_playing:
                await player.play()

            # 추가된 트랙 정보 UI 출력
            from lavalink.server import LoadType
            from tapi import SUCCESS_COLOR

            if results.load_type == LoadType.PLAYLIST:
                desc = (
                    f"▶️ 플레이리스트 **{results.playlist_info.name}** 에서 {added}곡이 추가되었습니다."
                )
            else:
                track = results.tracks[0]
                desc = f"▶️ **{track.title}** - {track.author}"

            notify_layout = ui.LayoutView(timeout=None)
            notify_layout.add_item(
                make_themed_container(
                    ui.TextDisplay(desc),
                    accent_color=SUCCESS_COLOR,
                )
            )

            # Check autodel setting
            db = Database()
            if db.get_autodel(message.guild.id):
                await message.channel.send(view=notify_layout, delete_after=15)
            else:
                await message.channel.send(view=notify_layout)

        except Exception as e:
            LOGGER.error(f"Error in handle_autoplay_message: {e}")
