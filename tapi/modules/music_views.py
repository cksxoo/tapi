import discord
import lavalink

from tapi import (
    LOGGER,
    THEME_COLOR,
    IDLE_COLOR,
    APP_NAME_TAG_VER,
    APP_BANNER_URL,
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


class RecommendationView(discord.ui.View):
    def __init__(self, recommended_tracks, user_id, player, current_track, guild_id):
        super().__init__(timeout=120)  # 2분 후 만료
        self.recommended_tracks = recommended_tracks
        self.user_id = user_id
        self.guild_id = guild_id
        self.player = player
        self.current_track = current_track
        self.message = None

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.delete()
            except discord.NotFound:
                pass
            except discord.Forbidden:
                pass

    def create_select_options(self):
        """동적으로 select 옵션 생성"""
        options = []
        for i, track in enumerate(self.recommended_tracks[:5]):  # 최대 5개
            title = track.title[:45] + ("..." if len(track.title) > 45 else "")
            author = track.author[:40] + ("..." if len(track.author) > 40 else "")
            duration = lavalink.utils.format_time(track.duration)

            options.append(
                discord.SelectOption(
                    label=f"{i+1}. {title}",
                    description=f"{author} - {duration}",
                    value=str(i),
                    emoji="🎵",
                )
            )
        return options

    async def create_select_view(self):
        """select 컴포넌트를 동적으로 추가"""
        select = discord.ui.Select(
            placeholder="Select a song...",  # 하드코딩 (interaction 없음)
            min_values=1,
            max_values=1,
            options=self.create_select_options(),
        )
        select.callback = self.select_recommendation_callback
        self.add_item(select)

    async def select_recommendation_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        # Select 컴포넌트에서 선택된 값 가져오기
        select = None
        for item in self.children:
            if isinstance(item, discord.ui.Select):
                select = item
                break

        if not select or not select.values:
            return

        selected_index = int(select.values[0])
        selected_track = self.recommended_tracks[selected_index]

        try:
            # 선택된 곡을 큐에 추가
            self.player.add(requester=self.user_id, track=selected_track)

            # 성공 메시지
            embed = discord.Embed(
                title=get_lan(interaction, "music_recommend_added_title"),
                description=f"**[{selected_track.title}]({selected_track.uri})**\n{selected_track.author}",
                color=THEME_COLOR,
            )

            # 추가된 곡 썸네일
            thumbnail_url = get_track_thumbnail(selected_track)
            if thumbnail_url:
                embed.set_thumbnail(url=thumbnail_url)

            embed.set_footer(text=get_lan(interaction, "music_recommend_added_footer"))

            # 원래 메시지는 그대로 두고, 새로운 공개 메시지로 성공 알림
            await send_temp_message(interaction, embed)
            # 원래 추천 메시지는 삭제
            await interaction.delete_original_response()

        except Exception as e:
            LOGGER.error(f"Error adding recommended track: {e}")
            await interaction.edit_original_response(
                content=f"곡 추가 중 오류가 발생했습니다: {str(e)}",
                embed=None,
                view=None,
            )

    @discord.ui.button(
        emoji="⭐", label="Add all!", style=discord.ButtonStyle.primary, row=1
    )
    async def add_all_recommendations(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()

        added_count = 0
        try:
            for track in self.recommended_tracks:
                try:
                    self.player.add(requester=self.user_id, track=track)
                    added_count += 1
                except Exception as e:
                    LOGGER.error(f"Error adding track: {e}")

            if added_count > 0:
                embed = discord.Embed(
                    title=get_lan(interaction, "music_recommend_all_added_title"),
                    description=get_lan(
                        interaction, "music_recommend_all_added_description"
                    ).format(track_title=self.current_track.title, count=added_count),
                    color=THEME_COLOR,
                )

                # 현재 곡 썸네일
                thumbnail_url = get_track_thumbnail(self.current_track)
                if thumbnail_url:
                    embed.set_thumbnail(url=thumbnail_url)

                embed.set_footer(
                    text=get_lan(
                        interaction, "music_recommend_all_added_footer"
                    ).format(count=added_count)
                )
            else:
                embed = discord.Embed(
                    title=get_lan(interaction, "music_recommend_all_failed"),
                    description=get_lan(
                        interaction, "music_recommend_all_failed_description"
                    ),
                    color=THEME_COLOR,
                )

            # 새로운 공개 메시지로 성공 알림
            await send_temp_message(interaction, embed)
            # 원래 추천 메시지는 삭제
            await interaction.delete_original_response()

        except Exception as e:
            LOGGER.error(f"Error adding all recommendations: {e}")
            await interaction.edit_original_response(
                content=f"곡 추가 중 오류가 발생했습니다: {str(e)}",
                embed=None,
                view=None,
            )

    @discord.ui.button(
        label="(´･ω･`) Nevermind", style=discord.ButtonStyle.danger, row=1
    )
    async def cancel_recommendations(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()

        embed = discord.Embed(
            title=get_lan(interaction, "music_recommend_cancelled"),
            description=get_lan(interaction, "music_recommend_cancelled_description"),
            color=THEME_COLOR,
        )

        # 원래 추천 메시지 완전 삭제
        await interaction.delete_original_response()
        # 취소 메시지를 임시로 표시
        await send_temp_message(interaction, embed)


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
        title = format_text_with_limit(track.title, 25)
        artist_name = format_text_with_limit(track.author, 25)

        return f"> [{title}]({track.uri})\n> {artist_name}\n> {progress_bar}\n> {time}"

    def _get_track_thumbnail(self, track) -> str:
        """트랙의 썸네일 URL 가져오기 (Spotify, YouTube 등 모든 소스 지원)"""
        return get_track_thumbnail(track)

    def _add_status_fields(self, embed, interaction, player):
        """상태 정보 필드 추가"""
        # 셔플 상태
        embed.add_field(
            name=get_lan(interaction, "music_shuffle"),
            value=(
                get_lan(interaction, "music_shuffle_already_on")
                if player.shuffle
                else get_lan(interaction, "music_shuffle_already_off")
            ),
            inline=True,
        )

        # 반복 상태
        repeat_values = [
            get_lan(interaction, "music_repeat_already_off"),
            get_lan(interaction, "music_repeat_already_one"),
            get_lan(interaction, "music_repeat_already_on"),
        ]
        embed.add_field(
            name=get_lan(interaction, "music_repeat"),
            value=repeat_values[player.loop],
            inline=True,
        )

        # 볼륨 상태
        embed.add_field(
            name=get_lan(interaction, "music_volume"),
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
        # embed = discord.Embed(color=IDLE_COLOR)
        # embed.title = f"<:audio:1399724398520434791> TAPI PLAYER ヾ(｡>﹏<｡)ﾉﾞ✧"

        embed = discord.Embed(color=0xFF6600)  # 할로윈 호박색
        embed.set_author(
            name="👻 TAPI PLAYER ヾ(｡>﹏<｡)ﾉﾞ✧",
        )

        embed.description = self._create_embed_description(track, progress_bar, time)
        
        # 상태 정보 추가
        self._add_status_fields(embed, interaction, player)

        # 썸네일 설정 (Spotify, YouTube 등 모든 소스 지원)
        thumbnail_url = self._get_track_thumbnail(track)
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)

        embed.set_image(url=APP_BANNER_URL)

        # embed.set_footer(text=APP_NAME_TAG_VER)
        embed.set_footer(
            text=f" {APP_NAME_TAG_VER} • Halloween Edition 🎃",
        )

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

        await player.skip()
        # 건너뛰기는 새 곡이 시작되면서 자동으로 새 컨트롤 패널이 나타남

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

    @discord.ui.button(
        emoji="💗",
        label="Recommend for You! (⁄ ⁄•⁄ω⁄•⁄ ⁄)⁄ ♡",
        style=discord.ButtonStyle.danger,
    )
    async def recommend(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """추천 곡 보기 버튼"""
        await interaction.response.defer()

        player = self.cog.bot.lavalink.player_manager.get(self.guild_id)
        if not player or not player.current:
            return await interaction.followup.send(
                get_lan(interaction, "music_recommend_no_playing"),
                ephemeral=True,
            )

        current_track = player.current

        # 현재 곡이 YouTube 곡인지 확인
        if not current_track.identifier:
            return await interaction.followup.send(
                get_lan(interaction, "music_recommend_youtube_only"),
                ephemeral=True,
            )

        # RD 라디오 URL 생성
        radio_url = f"https://www.youtube.com/watch?v={current_track.identifier}&list=RD{current_track.identifier}"

        try:
            # 라디오 추천 곡들 가져오기
            results = await player.node.get_tracks(radio_url)

            if not results or not results.tracks or len(results.tracks) <= 1:
                return await interaction.followup.send(
                    get_lan(interaction, "music_recommend_not_found"),
                    ephemeral=True,
                )

            # 첫 번째 곡은 현재 곡이므로 제외하고 상위 5곡
            recommended_tracks = results.tracks[1:6]

            if not recommended_tracks:
                return await interaction.followup.send(
                    get_lan(interaction, "music_recommend_failed"),
                    ephemeral=True,
                )

            # 추천 곡 리스트 View 생성
            recommend_view = RecommendationView(
                recommended_tracks, interaction.user.id, player, current_track, interaction.guild.id
            )
            await recommend_view.create_select_view()  # select 컴포넌트 동적 추가

            # 추천 곡 리스트 embed 생성
            embed = discord.Embed(
                title=get_lan(interaction, "music_recommend_title"),
                description=get_lan(
                    interaction, "music_recommend_description"
                ).format(track_title=current_track.title),
                color=THEME_COLOR,
            )

            for i, track in enumerate(recommended_tracks, 1):
                duration = lavalink.utils.format_time(track.duration)
                embed.add_field(
                    name=f"{i}. {track.title[:50]}{'...' if len(track.title) > 50 else ''}",
                    value=f"{track.author[:30]}{'...' if len(track.author) > 30 else ''} - {duration}",
                    inline=False,
                )

            embed.set_footer(
                text=get_lan(interaction, "music_recommend_footer")
            )

            # 현재 곡 썸네일 추가
            thumbnail_url = get_track_thumbnail(current_track)
            if thumbnail_url:
                embed.set_thumbnail(url=thumbnail_url)

            message = await interaction.followup.send(
                embed=embed, view=recommend_view, ephemeral=False
            )
            recommend_view.message = message

        except Exception as e:
            LOGGER.error(f"Error in recommend button: {e}")
            await interaction.followup.send(
                f"{get_lan(interaction, 'music_recommend_error')}: {str(e)}",
                ephemeral=True,
            )