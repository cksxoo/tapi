import discord
from discord import ui
import lavalink

from tapi import (
    LOGGER,
    THEME_COLOR,
    APP_NAME_TAG_VER,
    INFO_COLOR,
)
from tapi.utils.language import get_lan
from tapi.utils.database import Database
from tapi.utils.embed import format_text_with_limit, get_track_thumbnail
from tapi.utils.v2_components import (
    make_themed_container, make_separator, make_banner_gallery,
    make_invisible_spacer, get_platform_emoji,
)


# ============================================================
# Search
# ============================================================

class SearchSelect(ui.Select):
    """검색 결과 드롭다운 셀렉트"""
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


class SearchLayout(ui.LayoutView):
    """V2 검색 결과 레이아웃"""
    def __init__(self, tracks, cog, interaction):
        super().__init__(timeout=30)
        self.message = None

        title = get_lan(interaction, "music_search_results")
        subtitle = get_lan(interaction, "music_search_select")

        result_lines = []
        for i, track in enumerate(tracks, start=1):
            duration = lavalink.format_time(track.duration)
            emoji = get_platform_emoji(track)
            result_lines.append(
                f"**{i}.** {emoji} [{track.title}]({track.uri})\n> *{track.author}* `{duration}`"
            )
        result_text = "\n\n".join(result_lines)

        select = SearchSelect(tracks, cog, interaction)

        self.add_item(make_themed_container(
            ui.TextDisplay(f"## {title}"),
            ui.TextDisplay(f"-# {subtitle}"),
            make_separator(),
            ui.TextDisplay(result_text),
            make_invisible_spacer(),
            ui.ActionRow(select),
            accent_color=INFO_COLOR,
        ))

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.delete()
            except (discord.NotFound, discord.Forbidden):
                pass


# ============================================================
# Queue Select (공유 컴포넌트)
# ============================================================

class QueueSelect(ui.Select):
    """재생목록 드롭다운 셀렉트 (Now Playing, Queue에서 공유)"""
    def __init__(self, player, guild_id):
        self.player = player
        self.guild_id = guild_id

        options = []
        for i, track in enumerate(player.queue[:25], start=1):
            title = track.title[:80] if len(track.title) <= 80 else track.title[:77] + "..."
            author = track.author[:80] if len(track.author) <= 80 else track.author[:77] + "..."
            duration = lavalink.utils.format_time(track.duration)

            emoji = get_platform_emoji(track)

            options.append(
                discord.SelectOption(
                    label=f"{i}. {title}",
                    description=f"♪ {author} • {duration}",
                    value=str(i - 1),
                    emoji=emoji,
                )
            )

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
            disabled=len(player.queue) == 0,
        )

    async def callback(self, interaction: discord.Interaction):
        """재생목록에서 곡 선택 시 해당 곡으로 건너뛰기"""
        await interaction.response.defer()

        if self.values[0] == "empty":
            return

        queue_index = int(self.values[0])

        try:
            cog = interaction.client.get_cog("Music")
            if cog:
                cog._save_user_locale(interaction)

            if queue_index >= len(self.player.queue):
                return

            # 선택한 트랙을 큐에서 빼서 맨 앞에 삽입
            selected_track = self.player.queue.pop(queue_index)
            self.player.queue.insert(0, selected_track)

            # 현재 곡 정지 후 다음 곡(= 선택한 곡) 재생
            original_loop = self.player.loop
            if original_loop == 1:
                self.player.set_loop(0)

            current_track = self.player.current
            await self.player.stop()

            if self.player.loop == 2 and current_track:
                self.player.queue.append(current_track)

            await self.player.play()

            if original_loop == 1:
                self.player.set_loop(1)
                Database().set_loop(self.guild_id, 1)

        except Exception as e:
            LOGGER.error(f"Error skipping to queue position: {e}")
            await interaction.followup.send(
                get_lan(interaction, "music_queue_skip_failed"),
                ephemeral=True,
            )


# ============================================================
# Queue Paginator
# ============================================================

QUEUE_TEXT_ID = 1100
QUEUE_PAGE_ID = 1101


class QueueNavButton(ui.Button):
    """큐 페이지 네비게이션 버튼"""
    def __init__(self, label, direction, disabled=False):
        style = discord.ButtonStyle.gray
        if direction == 0:
            disabled = True
        super().__init__(label=label, style=style, disabled=disabled)
        self.direction = direction

    async def callback(self, interaction: discord.Interaction):
        view: QueuePaginatorLayout = self.view
        await view.navigate(interaction, self.direction)


class QueuePaginatorLayout(ui.LayoutView):
    """V2 큐 페이지네이션 레이아웃"""
    ITEMS_PER_PAGE = 10

    def __init__(self, interaction, player, pages, current_page=0):
        super().__init__(timeout=30)
        self.player = player
        self.pages = pages
        self.current_page = current_page
        self.interaction = interaction
        self.message = None

        queue_text, page_text = self._build_page_text(interaction)

        self.add_item(make_themed_container(
            ui.TextDisplay(queue_text, id=QUEUE_TEXT_ID),
            make_separator(),
            ui.TextDisplay(page_text, id=QUEUE_PAGE_ID),
            ui.ActionRow(
                QueueNavButton("◀ Prev", -1),
                QueueNavButton(f"Page {self.current_page + 1}/{len(self.pages)}", 0),
                QueueNavButton("Next ▶", 1),
            ),
        ))

    def _build_page_text(self, interaction):
        queue_list = ""
        start_index = self.current_page * self.ITEMS_PER_PAGE
        for index, track in enumerate(self.pages[self.current_page], start=start_index + 1):
            title = format_text_with_limit(track.title, 30)
            artist = format_text_with_limit(track.author, 30)
            duration = lavalink.utils.format_time(track.duration)
            queue_list += f"`{index}.` **[{title}]({track.uri})**\n> *{artist}* `{duration}`\n"

        header = f"## Queue  `{len(self.player.queue)} tracks`\n\n{queue_list}"
        page_info = f"-# Page {self.current_page + 1}/{len(self.pages)} | {APP_NAME_TAG_VER}"
        return header, page_info

    async def navigate(self, interaction, direction):
        self.current_page = (self.current_page + direction) % len(self.pages)
        queue_text, page_text = self._build_page_text(interaction)

        # Container 내부 아이템 업데이트
        container = self.children[0]
        queue_item = container.find_item(QUEUE_TEXT_ID)
        page_item = container.find_item(QUEUE_PAGE_ID)
        if queue_item:
            queue_item.content = queue_text
        if page_item:
            page_item.content = page_text

        # 네비게이션 버튼의 페이지 표시 업데이트
        action_row = None
        for child in container.children:
            if isinstance(child, ui.ActionRow):
                action_row = child
                break
        if action_row:
            for item in action_row.children:
                if isinstance(item, QueueNavButton) and item.direction == 0:
                    item.label = f"Page {self.current_page + 1}/{len(self.pages)}"

        await interaction.response.edit_message(view=self)

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.delete()
            except (discord.NotFound, discord.Forbidden):
                pass


# ============================================================
# Music Control - Now Playing Panel
# ============================================================

NP_TRACK_INFO_ID = 1001
NP_STATUS_ID = 1003


class MusicButton(ui.Button):
    """음악 컨트롤 버튼"""
    def __init__(self, action, **kwargs):
        super().__init__(**kwargs)
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        view: MusicControlLayout = self.view
        await interaction.response.defer()

        player = view.cog.bot.lavalink.player_manager.get(view.guild_id)
        if not player or not player.is_playing:
            return await interaction.followup.send(
                "음악이 재생되고 있지 않습니다!", ephemeral=True
            )

        if self.action == "pause_resume":
            await player.set_pause(not player.paused)

        elif self.action == "skip":
            if player.loop == 1:
                player.set_loop(2)
                Database().set_loop(view.guild_id, 2)
            view.cog._save_user_locale(interaction)
            await player.skip()
            return  # on_track_start가 새 메시지를 보냄

        elif self.action == "stop":
            if not interaction.guild.voice_client:
                return await interaction.followup.send(
                    get_lan(interaction, "music_dc_not_connect_voice_channel"),
                    ephemeral=True,
                )
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
            await view.cog._full_disconnect_cleanup(view.guild_id, "manual_disconnect_button")
            return await interaction.followup.send(
                get_lan(interaction, "music_dc_disconnected"),
                ephemeral=True,
            )

        elif self.action == "repeat":
            next_loop = (player.loop + 1) % 3
            player.set_loop(next_loop)
            Database().set_loop(view.guild_id, player.loop)

        elif self.action == "shuffle":
            player.set_shuffle(not player.shuffle)
            Database().set_shuffle(view.guild_id, player.shuffle)

        # 레이아웃 재빌드 및 업데이트
        new_layout = MusicControlLayout(view.cog, view.guild_id)
        new_layout.build_layout(interaction, player)
        await interaction.edit_original_response(view=new_layout)


class MusicControlLayout(ui.LayoutView):
    """V2 Now Playing 컨트롤 패널"""
    def __init__(self, cog, guild_id):
        super().__init__(timeout=7200)
        self.cog = cog
        self.guild_id = guild_id

    def build_layout(self, interaction, player):
        """현재 플레이어 상태로 레이아웃 구성"""
        track = player.current
        if not track:
            return None

        # 데이터 준비
        title = format_text_with_limit(track.title, 25)
        artist = format_text_with_limit(track.author, 25)
        platform_emoji = get_platform_emoji(track)
        thumbnail_url = get_track_thumbnail(track)

        # 상태 배지
        shuffle_label = get_lan(interaction, "music_shuffle")
        shuffle_value = get_lan(interaction, "music_shuffle_already_on" if player.shuffle else "music_shuffle_already_off")
        repeat_label = get_lan(interaction, "music_repeat")
        repeat_values = [
            get_lan(interaction, "music_repeat_already_off"),
            get_lan(interaction, "music_repeat_already_one"),
            get_lan(interaction, "music_repeat_already_on"),
        ]
        repeat_value = repeat_values[player.loop]
        volume_label = get_lan(interaction, "music_volume")
        status_text = f"**{shuffle_label}:** {shuffle_value}  ·  **{repeat_label}:** {repeat_value}  ·  **{volume_label}:** {player.volume}%"

        # 트랙 정보 텍스트
        track_info = f"> {platform_emoji} **[{title}]({track.uri})**\n> *{artist}*"

        # 버튼 생성
        pause_emoji = "<:play2:1433343063337467994>" if player.paused else "<:pause2:1433343068194734200>"
        pause_label = "Play " if player.paused else "Pause"

        pause_btn = MusicButton(action="pause_resume", emoji=pause_emoji, label=pause_label, style=discord.ButtonStyle.primary)
        skip_btn = MusicButton(action="skip", emoji="<:skip2:1433343066504433714>", label="Skip", style=discord.ButtonStyle.secondary)
        stop_btn = MusicButton(action="stop", emoji="<:stop2:1433343069935370240>", style=discord.ButtonStyle.danger)
        repeat_btn = MusicButton(action="repeat", emoji="<:repeat2:1433343061555150970>", label="Repeat", style=discord.ButtonStyle.secondary)
        shuffle_btn = MusicButton(
            action="shuffle",
            emoji="<:shuffle2:1433343064902205480>",
            label="Shuffle",
            style=discord.ButtonStyle.success if player.shuffle else discord.ButtonStyle.secondary,
        )

        # Queue Select
        queue_select = QueueSelect(player, self.guild_id)

        # Header with optional thumbnail
        header_title = ui.TextDisplay("### Now Playing")
        header_track = ui.TextDisplay(track_info, id=NP_TRACK_INFO_ID)

        # 레이아웃 조합
        self.clear_items()
        status_display = ui.TextDisplay(status_text, id=NP_STATUS_ID)
        header_items = []
        if thumbnail_url:
            header_items.append(ui.Section(
                header_title,
                header_track,
                status_display,
                accessory=ui.Thumbnail(thumbnail_url),
            ))
        else:
            header_items.append(header_title)
            header_items.append(header_track)
            header_items.append(status_display)

        self.add_item(ui.Container(
            *header_items,
            make_banner_gallery(),
            ui.ActionRow(pause_btn, skip_btn, stop_btn, repeat_btn, shuffle_btn),
            ui.ActionRow(queue_select),
            accent_colour=THEME_COLOR,
        ))

        return self
