import discord
import lavalink

from tapi import (
    LOGGER,
    THEME_COLOR,
    IDLE_COLOR,
    APP_BANNER_URL,
    BOT_VER,
)
from tapi.utils.language import get_lan
from tapi.utils.database import Database
from tapi.utils.embed import send_temp_message, format_text_with_limit, get_track_thumbnail


class SearchSelect(discord.ui.Select):
    def __init__(self, tracks, cog, interaction):
        self.tracks = tracks
        self.cog = cog
        self.interaction = interaction
        options = [
            discord.SelectOption(
                label=f"{i+1}. {track.title[:50]}",
                description=f"{track.author} - {lavalink.format_time(track.duration)}",
                value=str(i),
            )
            for i, track in enumerate(tracks)
        ]
        super().__init__(
            placeholder=get_lan(interaction, "music_search_select_placeholder"),
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        selected_index = int(self.values[0])
        selected_track = self.tracks[selected_index]
        await self.cog.play_search_result(interaction, selected_track)


class SearchView(discord.ui.View):
    def __init__(self, tracks, cog, interaction):
        super().__init__(timeout=30)
        self.add_item(SearchSelect(tracks, cog, interaction))
        self.message = None

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.delete()
            except discord.NotFound:
                pass
            except discord.Forbidden:
                pass


class QueueSelect(discord.ui.Select):
    def __init__(self, player, guild_id):
        self.player = player
        self.guild_id = guild_id

        # 재생목록에서 최대 25개 항목 가져오기 (Discord 제한)
        options = []

        for i, track in enumerate(player.queue[:25], start=1):
            # 제목과 아티스트 길이 제한
            title = track.title[:80] if len(track.title) <= 80 else track.title[:77] + "..."
            author = track.author[:80] if len(track.author) <= 80 else track.author[:77] + "..."
            duration = lavalink.utils.format_time(track.duration)

            # 트랙 출처에 따른 이모지 선택
            if track.uri:
                if "spotify.com" in track.uri or "spotify:" in track.uri:
                    emoji = "<:spotify:1433358080208404511>"
                elif "soundcloud.com" in track.uri:
                    emoji = "<:soundcloud:1433358078199201874>"
                elif "youtube.com" in track.uri or "youtu.be" in track.uri:
                    emoji = "<:youtube:1433358082028863519>"
                else:
                    emoji = "🎵"  # 기본 이모지
            else:
                emoji = "🎵"

            options.append(
                discord.SelectOption(
                    label=f"{i}. {title}",
                    description=f"♪ {author} • {duration}",
                    value=str(i - 1),  # 큐 인덱스 (0부터 시작)
                    emoji=emoji
                )
            )

        # 옵션이 없으면 더미 옵션 추가 (Discord는 최소 1개 옵션 필요)
        if not options:
            options = [discord.SelectOption(label="Empty", value="empty")]
            placeholder = "🎧 No tracks • Add music with /play"
        else:
            placeholder = f"🎧 {len(player.queue)} track{'s' if len(player.queue) > 1 else ''} in queue"

        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options,
            row=1,  # 두 번째 줄에 배치
            disabled=len(player.queue) == 0,  # 큐가 비어있으면 비활성화
        )

    async def callback(self, interaction: discord.Interaction):
        """재생목록에서 곡 선택 시 해당 곡으로 건너뛰기"""
        await interaction.response.defer()

        if self.values[0] == "empty":
            return

        queue_index = int(self.values[0])

        try:
            # 사용자 locale 저장 (on_track_start에서 사용)
            cog = interaction.client.get_cog("Music")
            if cog:
                cog._save_user_locale(interaction)

            # 한 곡 반복모드일 때는 임시로 해제
            original_loop = self.player.loop
            if original_loop == 1:
                self.player.set_loop(0)

            # 현재 재생 중인 곡 저장
            current_track = self.player.current

            # 현재 곡 stop
            await self.player.stop()

            # 전체 반복 모드면 현재 곡도 큐의 끝으로 이동
            if self.player.loop == 2 and current_track:
                self.player.queue.append(current_track)

            # 선택한 곡 이전의 모든 곡 처리
            for _ in range(queue_index):
                if self.player.queue:
                    track = self.player.queue.pop(0)
                    # 전체 반복 모드면 큐의 끝으로 이동
                    if self.player.loop == 2:
                        self.player.queue.append(track)

            # 이제 다음 곡(선택한 곡) 재생
            await self.player.play()

            # 반복 모드 복원
            if original_loop == 1:
                self.player.set_loop(1)
                from tapi.utils.database import Database
                Database().set_loop(self.guild_id, 1)

        except Exception as e:
            LOGGER.error(f"Error skipping to queue position: {e}")
            await interaction.followup.send(
                get_lan(interaction, "music_queue_skip_failed"),
                ephemeral=True
            )


class MusicControlView(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=7200)  # 2시간 후 버튼 비활성화
        self.cog = cog
        self.guild_id = guild_id

        # 플레이어 상태에 따라 버튼 초기 상태 설정
        try:
            player = cog.bot.lavalink.player_manager.get(guild_id)
            if player:
                # 일시정지 버튼 상태
                if player.paused:
                    self.pause_resume.emoji = "<:play2:1433343063337467994>"
                    self.pause_resume.label = "Play "
                else:
                    self.pause_resume.emoji = "<:pause2:1433343068194734200>"
                    self.pause_resume.label = "Pause"

                # 반복 버튼 상태
                self.repeat.emoji = "<:repeat2:1433343061555150970>"

                # 셔플 버튼 상태
                self.shuffle.style = (
                    discord.ButtonStyle.success
                    if player.shuffle
                    else discord.ButtonStyle.secondary
                )

                # 재생목록 Select 메뉴 추가 (항상 표시)
                self.add_item(QueueSelect(player, guild_id))
        except (AttributeError, ValueError, KeyError):
            pass  # 오류 시 기본 상태 유지

    def create_progress_bar(self, current, total, length=20):
        """유니코드 문자로 진행률 바 생성"""
        if total == 0:
            return "`" + "░" * length + "` 00:00/00:00"

        filled = int((current / total) * length)
        bar = "█" * filled + "░" * (length - filled)
        current_time = lavalink.utils.format_time(current)
        total_time = lavalink.utils.format_time(total)
        time = f"{current_time}/{total_time}"
        return f"`{bar}`", f"{time}"


    def _create_embed_description(self, track, progress_bar: str, time: str) -> str:
        """embed 설명 생성"""
        # 제목 길이를 더 짧게 (30 -> 20)
        title = format_text_with_limit(track.title, 20)
        artist_name = format_text_with_limit(track.author, 20)

        # 플랫폼 이모지 선택
        platform_emoji = "🎵"  # 기본
        if track.uri:
            if "spotify.com" in track.uri or "spotify:" in track.uri:
                platform_emoji = "<:spotify:1433358080208404511>"
            elif "soundcloud.com" in track.uri:
                platform_emoji = "<:soundcloud:1433358078199201874>"
            elif "youtube.com" in track.uri or "youtu.be" in track.uri:
                platform_emoji = "<:youtube:1433358082028863519>"

        return f"> {platform_emoji} [{title}]({track.uri})\n> {artist_name}\n> {progress_bar}\n> {time}"

    def _get_track_thumbnail(self, track) -> str:
        """트랙의 썸네일 URL 가져오기 (Spotify, YouTube 등 모든 소스 지원)"""
        return get_track_thumbnail(track)

    def _add_status_fields(self, embed, interaction, player):
        """상태 정보 필드 추가"""
        # 셔플 상태
        shuffle_value = (
            get_lan(interaction, "music_shuffle_already_on")
            if player.shuffle
            else get_lan(interaction, "music_shuffle_already_off")
        )
        embed.add_field(
            # name=f"{get_lan(interaction, 'music_shuffle')} <a:deco:1445971839661641749>",
            name=f"{get_lan(interaction, 'music_shuffle')}",
            value=shuffle_value,
            inline=True,
        )

        # 반복 상태
        repeat_values = [
            get_lan(interaction, "music_repeat_already_off"),
            get_lan(interaction, "music_repeat_already_one"),
            get_lan(interaction, "music_repeat_already_on"),
        ]
        embed.add_field(
            # name=f"{get_lan(interaction, 'music_repeat')} <a:deco2:1445972175432581221>",
            name=f"{get_lan(interaction, 'music_repeat')}",
            value=repeat_values[player.loop],
            inline=True,
        )

        # 볼륨 상태
        embed.add_field(
            # name=f"{get_lan(interaction, 'music_volume')} <a:deco3:1445971923308908607>",
            name=f"{get_lan(interaction, 'music_volume')}",
            value=f"{player.volume}%",
            inline=True,
        )

    def _update_button_states(self, player):
        """모든 버튼 상태 업데이트"""
        # 일시정지/재생 버튼
        if player.paused:
            self.pause_resume.emoji = "<:play2:1433343063337467994>"
            self.pause_resume.label = "Play "
        else:
            self.pause_resume.emoji = "<:pause2:1433343068194734200>"
            self.pause_resume.label = "Pause"

        # 반복 버튼
        self.repeat.emoji = "<:repeat2:1433343061555150970>"

        # 셔플 버튼
        self.shuffle.style = (
            discord.ButtonStyle.success
            if player.shuffle
            else discord.ButtonStyle.secondary
        )

    def update_embed_and_buttons(self, interaction, player):
        """embed와 모든 버튼 상태를 현재 플레이어 상태로 업데이트"""
        track = player.current
        if not track:
            return None

        # 진행률 바 생성
        progress_bar, time = self.create_progress_bar(player.position, track.duration)

        # embed 생성
        embed = discord.Embed(color=THEME_COLOR)
        embed.set_author(
            name="TAPI PLAYER",
            icon_url="https://cdn.discordapp.com/emojis/1455018743351742546.gif"
            # name="TAPI PLAYER ヾ(｡>﹏<｡)ﾉﾞ✧",  # Original
            # icon_url="https://cdn.discordapp.com/emojis/1433353546778153014.gif"  # Original
        )

        embed.description = self._create_embed_description(track, progress_bar, time)

        # 상태 정보 추가
        self._add_status_fields(embed, interaction, player)

        # 썸네일 설정 (Spotify, YouTube 등 모든 소스 지원)
        thumbnail_url = self._get_track_thumbnail(track)
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)

        embed.set_image(url=APP_BANNER_URL)
        
        # Footer 설정 (주석 처리됨)
        # embed.set_footer(
        #     text=f"𝓒𝓱𝓻𝓲𝓼𝓽𝓶𝓪𝓼 𝓔𝓭𝓲𝓽𝓲𝓸𝓷 | {BOT_VER}",
        #     icon_url="https://cdn.discordapp.com/emojis/1445968171969417388.gif"
        # )

        # 버튼 상태 업데이트
        self._update_button_states(player)
        
        return embed

    @discord.ui.button(
        emoji="<:pause2:1433343068194734200>",
        label="Pause",
        style=discord.ButtonStyle.primary,
    )
    async def pause_resume(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """일시정지/재생 버튼"""
        await interaction.response.defer()

        player = self.cog.bot.lavalink.player_manager.get(self.guild_id)
        if not player or not player.is_playing:
            return await interaction.followup.send(
                "음악이 재생되고 있지 않습니다!", ephemeral=True
            )

        if player.paused:
            await player.set_pause(False)
        else:
            await player.set_pause(True)

        # embed와 모든 버튼 상태 업데이트
        embed = self.update_embed_and_buttons(interaction, player)
        if embed:
            await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(
        emoji="<:skip2:1433343066504433714>",
        label="Skip",
        style=discord.ButtonStyle.secondary,
    )
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        """건너뛰기 버튼"""
        await interaction.response.defer()

        player = self.cog.bot.lavalink.player_manager.get(self.guild_id)
        if not player or not player.is_playing:
            return await interaction.followup.send(
                "음악이 재생되고 있지 않습니다!", ephemeral=True
            )

        # 한 곡 반복모드일 때는 전체 반복으로 전환 후 skip
        if player.loop == 1:  # 한 곡 반복모드
            player.set_loop(2)  # 전체 반복으로 전환
            from tapi.utils.database import Database
            Database().set_loop(self.guild_id, 2)  # 설정 저장

        # 사용자 locale 저장 (on_track_start에서 사용)
        self.cog._save_user_locale(interaction)

        await player.skip()
        # on_track_start 이벤트가 자동으로 사용자 언어로 embed를 업데이트함

    @discord.ui.button(
        emoji="<:stop2:1433343069935370240>",
        style=discord.ButtonStyle.danger,
    )
    async def disconnect(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """연결 종료 버튼"""
        await interaction.response.defer()

        player = self.cog.bot.lavalink.player_manager.get(self.guild_id)
        if not player:
            return await interaction.followup.send(
                get_lan(interaction, "music_dc_not_connect_voice_channel"),
                ephemeral=True,
            )

        # 음성 채널 확인
        if not interaction.guild.voice_client:
            return await interaction.followup.send(
                get_lan(interaction, "music_dc_not_connect_voice_channel"),
                ephemeral=True,
            )

        # 사용자가 같은 음성 채널에 있는지 확인
        if not interaction.user.voice or (
            player.is_connected
            and interaction.user.voice.channel.id != int(player.channel_id)
        ):
            return await interaction.followup.send(
                get_lan(interaction, "music_dc_not_connect_my_voice_channel").format(
                    name=interaction.user.name
                ),
                ephemeral=True,
            )

        # 연결 종료 처리
        await self.cog._full_disconnect_cleanup(
            self.guild_id,
            "manual_disconnect_button",
        )

        await interaction.followup.send(
            get_lan(interaction, "music_dc_disconnected"),
            ephemeral=True,
        )

    @discord.ui.button(
        emoji="<:repeat2:1433343061555150970>",
        label="Repeat",
        style=discord.ButtonStyle.secondary,
    )
    async def repeat(self, interaction: discord.Interaction, button: discord.ui.Button):
        """반복 모드 버튼 (off → 전곡 → 한곡 → off 순환)"""
        await interaction.response.defer()

        player = self.cog.bot.lavalink.player_manager.get(self.guild_id)
        if not player or not player.is_playing:
            return await interaction.followup.send(
                "음악이 재생되고 있지 않습니다!", ephemeral=True
            )

        # 반복 모드 순환: 0(off) → 1(한곡) → 2(전곡) → 0(off)
        next_loop = (player.loop + 1) % 3
        player.set_loop(next_loop)

        # 데이터베이스에 설정 저장
        Database().set_loop(self.guild_id, player.loop)

        # embed와 모든 버튼 상태 업데이트
        embed = self.update_embed_and_buttons(interaction, player)
        if not embed:
            return
            
        await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(
        emoji="<:shuffle2:1433343064902205480>",
        label="Shuffle",
        style=discord.ButtonStyle.secondary,
    )
    async def shuffle(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """셔플 모드 토글 버튼"""
        await interaction.response.defer()

        player = self.cog.bot.lavalink.player_manager.get(self.guild_id)
        if not player or not player.is_playing:
            return await interaction.followup.send(
                "음악이 재생되고 있지 않습니다!", ephemeral=True
            )

        # 셔플 모드 토글
        player.set_shuffle(not player.shuffle)

        # 데이터베이스에 설정 저장
        Database().set_shuffle(self.guild_id, player.shuffle)

        # embed와 모든 버튼 상태 업데이트
        embed = self.update_embed_and_buttons(interaction, player)
        if not embed:
            return
            
        await interaction.edit_original_response(embed=embed, view=self)

