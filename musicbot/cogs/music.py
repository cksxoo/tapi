import re
import os
import math
import difflib
import traceback
from sclib import SoundcloudAPI

import discord
from discord import app_commands

# from discord import option
from discord.ext import commands

# from discord.ext import commands, pages

import lavalink
from lavalink.events import TrackStartEvent, QueueEndEvent
from lavalink.errors import ClientError
from lavalink.server import LoadType

from musicbot.utils.language import get_lan
from musicbot.utils.volumeicon import volumeicon
from musicbot.utils.get_chart import get_melon, get_billboard, get_billboardjp
from musicbot.utils.play_list import play_list
from musicbot.utils.statistics import Statistics
from musicbot import (
    LOGGER,
    BOT_ID,
    COLOR_CODE,
    BOT_NAME_TAG_VER,
    HOST,
    PSW,
    REGION,
    PORT,
)
from musicbot.utils.equalizer import Equalizer, EqualizerButton
from musicbot.utils.database import Database

url_rx = re.compile(r"https?://(?:www\.)?.+")


class LavalinkVoiceClient(discord.VoiceClient):
    """
    This is the preferred way to handle external voice sending
    This client will be created via a cls in the connect method of the channel
    see the following documentation:
    https://discordpy.readthedocs.io/en/latest/api.html#voiceprotocol
    """

    def __init__(self, client: discord.Client, channel: discord.abc.Connectable):
        self.client = client
        self.channel = channel
        self.guild_id = channel.guild.id
        self._destroyed = False

        if not hasattr(self.client, "lavalink"):
            # Instantiate a client if one doesn't exist.
            # We store it in `self.client` so that it may persist across cog reloads,
            # however this is not mandatory.
            self.client.lavalink = lavalink.Client(client.user.id)
            self.client.lavalink.add_node(
                host=HOST, port=PORT, password=PSW, region=REGION, name="default-node"
            )

        # Create a shortcut to the Lavalink client here.
        self.lavalink = self.client.lavalink

    async def on_voice_server_update(self, data):
        # the data needs to be transformed before being handed down to
        # voice_update_handler
        lavalink_data = {"t": "VOICE_SERVER_UPDATE", "d": data}
        await self.lavalink.voice_update_handler(lavalink_data)

    async def on_voice_state_update(self, data):
        channel_id = data["channel_id"]

        if not channel_id:
            await self._destroy()
            return

        self.channel = self.client.get_channel(int(channel_id))

        # the data needs to be transformed before being handed down to
        # voice_update_handler
        lavalink_data = {"t": "VOICE_STATE_UPDATE", "d": data}

        await self.lavalink.voice_update_handler(lavalink_data)

    async def connect(
        self,
        *,
        timeout: float,
        reconnect: bool,
        self_deaf: bool = False,
        self_mute: bool = False,
    ) -> None:
        """
        Connect the bot to the voice channel and create a player_manager
        if it doesn't exist yet.
        """
        # ensure there is a player_manager when creating a new voice_client
        self.lavalink.player_manager.create(guild_id=self.channel.guild.id)
        await self.channel.guild.change_voice_state(
            channel=self.channel, self_mute=self_mute, self_deaf=self_deaf
        )

    async def disconnect(self, *, force: bool = False) -> None:
        """
        Handles the disconnect.
        Cleans up running player and leaves the voice client.
        """
        player = self.lavalink.player_manager.get(self.channel.guild.id)

        if player is not None:
            # no need to disconnect if we are not connected
            if not force and not player.is_connected:
                return

            # None means disconnect
            await self.channel.guild.change_voice_state(channel=None)

            # update the channel_id of the player to None
            # this must be done because the on_voice_state_update that would set channel_id
            # to None doesn't get dispatched after the disconnect
            player.channel_id = None
            await self._destroy()

    async def _destroy(self):
        self.cleanup()

        if self._destroyed:
            # Idempotency handling, if `disconnect()` is called, the changed voice state
            # could cause this to run a second time.
            return

        self._destroyed = True

        try:
            await self.lavalink.player_manager.destroy(self.guild_id)
        except ClientError:
            pass


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        if not hasattr(
            bot, "lavalink"
        ):  # This ensures the client isn't overwritten during cog reloads.
            bot.lavalink = lavalink.Client(BOT_ID)
            bot.lavalink.add_node(
                host=HOST, port=PORT, password=PSW, region=REGION, name="default-node"
            )

        self.lavalink = bot.lavalink
        self.lavalink.add_event_hooks(self)

    def cog_unload(self):
        """Cog unload handler. This removes any event hooks that were registered."""
        self.bot.lavalink._event_hooks.clear()

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            embed = discord.Embed(
                title=error.original, description="", color=COLOR_CODE
            )
            embed.set_footer(text=BOT_NAME_TAG_VER)
            await ctx.respond(embed=embed)
            # The above handles errors thrown in this cog and shows them to the user.
            # This shouldn't be a problem as the only errors thrown in this cog are from `ensure_voice`
            # which contain a reason string, such as "Join a voicechannel" etc. You can modify the above
            # if you want to do things differently.
        else:
            print(traceback.format_exc())

    async def create_player(interaction: discord.Interaction):
        """
        A check that is invoked before any commands marked with `@app_commands.check(create_player)` can run.

        This function will try to create a player for the guild associated with this Interaction, or raise
        an error which will be relayed to the user if one cannot be created.
        """
        if interaction.guild is None:
            raise app_commands.NoPrivateMessage()

        try:
            player = interaction.client.lavalink.player_manager.create(
                interaction.guild.id
            )
        except Exception as e:
            LOGGER.error(f"Failed to create player: {e}")
            LOGGER.error(
                f"Lavalink connection details: HOST={HOST}, PORT={PORT}, REGION={REGION}"
            )
            raise
        # Create returns a player if one exists, otherwise creates.
        # This line is important because it ensures that a player always exists for a guild.

        # Most people might consider this a waste of resources for guilds that aren't playing, but this is
        # the easiest and simplest way of ensuring players are created.

        # These are commands that require the bot to join a voicechannel (i.e. initiating playback).
        # Commands such as volume/skip etc don't require the bot to be in a voicechannel so don't need listing here.
        should_connect = interaction.command.name in (
            "play",
            "scplay",
            "search",
            "connect",
            "list",
            "chartplay",
        )

        voice_client = interaction.guild.voice_client

        if not interaction.user.voice or not interaction.user.voice.channel:
            raise app_commands.CheckFailure(
                get_lan(interaction.user.id, "music_come_in_voice_channel")
            )

        voice_channel = interaction.user.voice.channel

        if voice_client is None:
            if not should_connect:
                raise app_commands.CheckFailure(
                    get_lan(interaction.user.id, "music_not_connected_voice_channel")
                )

            permissions = voice_channel.permissions_for(interaction.guild.me)

            if not permissions.connect or not permissions.speak:
                raise app_commands.CheckFailure(
                    get_lan(interaction.user.id, "music_no_permission")
                )

            if voice_channel.user_limit > 0:
                # A limit of 0 means no limit. Anything higher means that there is a member limit which we need to check.
                # If it's full, and we don't have "move members" permissions, then we cannot join it.
                if (
                    len(voice_channel.members) >= voice_channel.user_limit
                    and not interaction.guild.me.guild_permissions.move_members
                ):
                    raise app_commands.CheckFailure(
                        get_lan(interaction.user.id, "music_voice_channel_is_full")
                    )

            player.store("channel", interaction.channel.id)
            await interaction.user.voice.channel.connect(cls=LavalinkVoiceClient)
        elif voice_client.channel.id != voice_channel.id:
            raise app_commands.CheckFailure(
                get_lan(interaction.user.id, "music_come_in_my_voice_channel")
            )

        # 반복 상태 설정
        loop = Database().get_loop(interaction.guild.id)
        if loop is not None:
            player.set_loop(loop)

        # 셔플 상태 설정
        shuffle = Database().get_shuffle(interaction.guild.id)
        if shuffle is not None:
            player.set_shuffle(shuffle)

        # 볼륨 설정
        await player.set_volume(50)

        return True

    @lavalink.listener(TrackStartEvent)
    async def on_track_start(self, event: TrackStartEvent):
        guild_id = event.player.guild_id
        channel_id = event.player.fetch("channel")
        guild = self.bot.get_guild(guild_id)

        if not guild:
            return await self.lavalink.player_manager.destroy(guild_id)

        channel = guild.get_channel(channel_id)

        if channel:
            embed = discord.Embed(
                title="Now playing: {} by {}".format(
                    event.track.title, event.track.author
                ),
                color=COLOR_CODE,
            )
            embed.set_footer(text=BOT_NAME_TAG_VER)
            return await channel.send(embed=embed)

    @lavalink.listener(QueueEndEvent)
    async def on_queue_end(self, event: QueueEndEvent):
        guild_id = event.player.guild_id
        guild = self.bot.get_guild(guild_id)

        if guild is not None:
            await guild.voice_client.disconnect(force=True)

    @app_commands.command(name="connect", description="Connect to voice channel!")
    @app_commands.check(create_player)
    async def connect(self, interaction: discord.Interaction):
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        if not player.is_connected:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_connect_voice_channel"),
                color=COLOR_CODE,
            )
            embed.set_footer(text=BOT_NAME_TAG_VER)
            await interaction.response.send_message(embed=embed)
        embed = discord.Embed(
            title=get_lan(interaction.user.id, "music_already_connected_voice_channel"),
            color=COLOR_CODE,
        )
        embed.set_footer(text=BOT_NAME_TAG_VER)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="play", description="Searches and plays a song from a given query."
    )
    @app_commands.describe(query="찾고싶은 음악의 제목이나 링크를 입력하세요")
    @app_commands.check(create_player)
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        # Get the player for this guild from cache.
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        # Remove leading and trailing <>. <> may be used to suppress embedding links in Discord.
        query = query.strip("<>")

        # Check if the user input might be a URL. If it isn't, we can Lavalink do a YouTube search for it instead.
        # SoundCloud searching is possible by prefixing "scsearch:" instead.
        if not url_rx.match(query):
            query = f"ytsearch:{query}"

        nofind = 0
        while True:
            # Get the results for the query from Lavalink.
            results = await player.node.get_tracks(query)

            # Results could be None if Lavalink returns an invalid response (non-JSON/non-200 (OK)).
            # ALternatively, results['tracks'] could be an empty array if the query yielded no tracks.
            if results.load_type == LoadType.EMPTY or not results or not results.tracks:
                if nofind < 3:
                    nofind += 1
                elif nofind == 3:
                    embed = discord.Embed(
                        title=get_lan(
                            interaction.user.id, "music_can_not_find_anything"
                        ),
                        description="",
                        color=COLOR_CODE,
                    )
                    embed.set_footer(text=BOT_NAME_TAG_VER)
                    return await interaction.followup.send(embed=embed)
            else:
                break

        embed = discord.Embed(color=COLOR_CODE)  # discord.Color.blurple()

        # Valid load_types are:
        #   TRACK    - direct URL to a track
        #   PLAYLIST - direct URL to playlist
        #   SEARCH   - query prefixed with either "ytsearch:" or "scsearch:". This could possibly be expanded with plugins.
        #   EMPTY    - no results for the query (result.tracks will be empty)
        #   ERROR    - the track encountered an exception during loading
        thumbnail = None
        if results.load_type == LoadType.PLAYLIST:
            tracks = results.tracks

            trackcount = 0

            for track in tracks:
                if trackcount != 1:
                    thumbnail = track.identifier
                    trackcount = 1
                # Music statistical(for playlist)
                Statistics().up(track.identifier)

                # Add all of the tracks from the playlist to the queue.
                player.add(requester=interaction.user.id, track=track)

            embed.title = get_lan(interaction.user.id, "music_play_playlist")
            embed.description = f"{results.playlist_info.name} - {len(tracks)} tracks"

        else:
            track = results.tracks[0]
            embed.title = get_lan(interaction.user.id, "music_play_music")
            embed.description = f"[{track.title}]({track.uri})"
            thumbnail = track.identifier

            # Music statistical
            Statistics().up(track.identifier)

            # You can attach additional information to audiotracks through kwargs, however this involves
            # constructing the AudioTrack class yourself.
            player.add(requester=interaction.user.id, track=track)

        embed.add_field(
            name=get_lan(interaction.user.id, "music_shuffle"),
            value=(
                get_lan(interaction.user.id, "music_shuffle_already_on")
                if player.shuffle
                else get_lan(interaction.user.id, "music_shuffle_already_off")
            ),
            inline=True,
        )
        embed.add_field(
            name=get_lan(interaction.user.id, "music_repeat"),
            value=[
                get_lan(interaction.user.id, "music_repeat_already_off"),
                get_lan(interaction.user.id, "music_repeat_already_one"),
                get_lan(interaction.user.id, "music_repeat_already_on"),
            ][player.loop],
            inline=True,
        )

        if thumbnail is not None:
            embed.set_thumbnail(url=f"http://img.youtube.com/vi/{thumbnail}/0.jpg")
        embed.set_footer(text=BOT_NAME_TAG_VER)
        await interaction.followup.send(embed=embed)

        # We don't want to call .play() if the player is playing as that will effectively skip
        # the current track.
        if not player.is_playing:
            await player.play()

    @app_commands.command(
        name="scplay", description="Searches and plays a song from SoundCloud."
    )
    @app_commands.describe(
        query="SoundCloud에서 찾고싶은 음악의 제목이나 링크를 입력하세요"
    )
    @app_commands.check(create_player)
    async def scplay(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        # Get the player for this guild from cache.
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        # Remove leading and trailing <>. <> may be used to suppress embedding links in Discord.
        query = query.strip("<>")

        # Check if the user input might be a URL. If it isn't, we can Lavalink do a YouTube search for it instead.
        # SoundCloud searching is possible by prefixing "scsearch:" instead.
        if not url_rx.match(query):
            query = f"scsearch:{query}"

        nofind = 0
        while True:
            # Get the results for the query from Lavalink.
            results = await player.node.get_tracks(query)

            # Results could be None if Lavalink returns an invalid response (non-JSON/non-200 (OK)).
            # ALternatively, results['tracks'] could be an empty array if the query yielded no tracks.
            if results.load_type == LoadType.EMPTY or not results or not results.tracks:
                if nofind < 3:
                    nofind += 1
                elif nofind == 3:
                    embed = discord.Embed(
                        title=get_lan(
                            interaction.user.id, "music_can_not_find_anything"
                        ),
                        description="",
                        color=COLOR_CODE,
                    )
                    embed.set_footer(text=BOT_NAME_TAG_VER)
                    return await interaction.followup.send(embed=embed)
            else:
                break

        embed = discord.Embed(color=COLOR_CODE)  # discord.Color.blurple()

        # Valid load_types are:
        #   TRACK    - direct URL to a track
        #   PLAYLIST - direct URL to playlist
        #   SEARCH   - query prefixed with either "ytsearch:" or "scsearch:". This could possibly be expanded with plugins.
        #   EMPTY    - no results for the query (result.tracks will be empty)
        #   ERROR    - the track encountered an exception during loading
        thumbnail = None
        if results.load_type == LoadType.PLAYLIST:
            tracks = results.tracks

            trackcount = 0

            for track in tracks:
                if trackcount != 1:
                    thumbnail = track.uri
                    trackcount = 1
                # Music statistical(for playlist)
                # Statistics().up(track.identifier)

                # Add all of the tracks from the playlist to the queue.
                player.add(requester=interaction.user.id, track=track)

            embed.title = get_lan(interaction.user.id, "music_play_playlist")
            embed.description = f"{results.playlist_info.name} - {len(tracks)} tracks"

        else:
            track = results.tracks[0]
            embed.title = get_lan(interaction.user.id, "music_play_music")
            embed.description = f"[{track.title}]({track.uri})"
            thumbnail = track.uri

            # Music statistical
            # Statistics().up(track.identifier)

            # You can attach additional information to audiotracks through kwargs, however this involves
            # constructing the AudioTrack class yourself.
            player.add(requester=interaction.user.id, track=track)

        embed.add_field(
            name=get_lan(interaction.user.id, "music_shuffle"),
            value=(
                get_lan(interaction.user.id, "music_shuffle_already_on")
                if player.shuffle
                else get_lan(interaction.user.id, "music_shuffle_already_off")
            ),
            inline=True,
        )
        embed.add_field(
            name=get_lan(interaction.user.id, "music_repeat"),
            value=[
                get_lan(interaction.user.id, "music_repeat_already_off"),
                get_lan(interaction.user.id, "music_repeat_already_one"),
                get_lan(interaction.user.id, "music_repeat_already_on"),
            ][player.loop],
            inline=True,
        )

        if thumbnail is not None:
            track = SoundcloudAPI().resolve(thumbnail)
            if track.artwork_url is not None:
                embed.set_thumbnail(url=track.artwork_url)
        embed.set_footer(text=BOT_NAME_TAG_VER)
        await interaction.followup.send(embed=embed)

        # We don't want to call .play() if the player is playing as that will effectively skip
        # the current track.
        if not player.is_playing:
            await player.play()


    @app_commands.command(name="search", description="Search for songs with a given keyword")
    @app_commands.describe(query="Enter the keyword to search for songs")
    @app_commands.check(create_player)
    async def search(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        if not query:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_search_no_keyword"),
                color=COLOR_CODE
            )
            embed.set_footer(text=BOT_NAME_TAG_VER)
            return await interaction.followup.send(embed=embed)

        # Use ytsearch: prefix to search YouTube
        query = f"ytsearch:{query}"
        results = await player.node.get_tracks(query)

        if not results or not results.tracks:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_search_no_results"),
                color=COLOR_CODE
            )
            embed.set_footer(text=BOT_NAME_TAG_VER)
            return await interaction.followup.send(embed=embed)

        tracks = results.tracks[:5]  # Limit to 5 results

        embed = discord.Embed(
            title=get_lan(interaction.user.id, "music_search_results"),
            description=get_lan(interaction.user.id, "music_search_select"),
            color=COLOR_CODE
        )
        for i, track in enumerate(tracks, start=1):
            embed.add_field(
                name=f"{i}. {track.title}",
                value=f"{track.author} - {lavalink.format_time(track.duration)}",
                inline=False
            )
        embed.set_footer(text=BOT_NAME_TAG_VER)

        view = SearchView(tracks, self, interaction)
        await interaction.followup.send(embed=embed, view=view)

    async def play_search_result(self, interaction: discord.Interaction, track):
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        player.add(requester=interaction.user.id, track=track)

        embed = discord.Embed(color=COLOR_CODE)
        embed.title = get_lan(interaction.user.id, "music_play_music")
        embed.description = f"[{track.title}]({track.uri})"

        embed.add_field(
            name=get_lan(interaction.user.id, "music_shuffle"),
            value=(get_lan(interaction.user.id, "music_shuffle_already_on") if player.shuffle
                   else get_lan(interaction.user.id, "music_shuffle_already_off")),
            inline=True
        )
        embed.add_field(
            name=get_lan(interaction.user.id, "music_repeat"),
            value=[
                get_lan(interaction.user.id, "music_repeat_already_off"),
                get_lan(interaction.user.id, "music_repeat_already_one"),
                get_lan(interaction.user.id, "music_repeat_already_on")
            ][player.loop],
            inline=True
        )

        embed.set_thumbnail(url=f"http://img.youtube.com/vi/{track.identifier}/0.jpg")
        embed.set_footer(text=BOT_NAME_TAG_VER)
        await interaction.followup.send(embed=embed)

        if not player.is_playing:
            await player.play()


    @app_commands.command(
        name="disconnect",
        description="Disconnects the player from the voice channel and clears its queue.",
    )
    @app_commands.check(create_player)
    async def disconnect(self, interaction: discord.Interaction):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        if not interaction.guild.voice_client:
            embed = discord.Embed(
                title=get_lan(
                    interaction.user.id, "music_dc_not_connect_voice_channel"
                ),
                color=COLOR_CODE,
            )
            embed.set_footer(text=BOT_NAME_TAG_VER)
            return await interaction.followup.send(embed=embed)

        if not interaction.user.voice or (
            player.is_connected
            and interaction.user.voice.channel.id != int(player.channel_id)
        ):
            embed = discord.Embed(
                title=get_lan(
                    interaction.user.id, "music_dc_not_connect_my_voice_channel"
                ).format(name=interaction.user.name),
                color=COLOR_CODE,
            )
            embed.set_footer(text=BOT_NAME_TAG_VER)
            return await interaction.followup.send(embed=embed)

        player.queue.clear()
        await player.stop()
        await interaction.guild.voice_client.disconnect(force=True)

        embed = discord.Embed(
            title=get_lan(interaction.user.id, "music_dc_disconnected"),
            color=COLOR_CODE,
        )
        embed.set_footer(text=BOT_NAME_TAG_VER)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="skip", description="Skip to the next song!")
    @app_commands.check(create_player)
    async def skip(self, interaction: discord.Interaction):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        if not player.is_playing:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_not_playing"),
                description="",
                color=COLOR_CODE,
            )
            embed.set_footer(text=BOT_NAME_TAG_VER)
            return await interaction.followup.send(embed=embed)

        await player.skip()

        embed = discord.Embed(
            title=get_lan(interaction.user.id, "music_skip_next"),
            description="",
            color=COLOR_CODE,
        )
        embed.set_footer(text=BOT_NAME_TAG_VER)
        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="nowplaying", description="Sending the currently playing song!"
    )
    @app_commands.check(create_player)
    async def nowplaying(self, interaction: discord.Interaction):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        if not player.current:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_no_playing_music"),
                description="",
                color=COLOR_CODE,
            )
            embed.set_footer(text=BOT_NAME_TAG_VER)
            return await interaction.followup.send(embed=embed)

        position = lavalink.utils.format_time(player.position)
        if player.current.stream:
            duration = "🔴 LIVE"
        else:
            duration = lavalink.utils.format_time(player.current.duration)
        song = f"**[{player.current.title}]({player.current.uri})**\n({position}/{duration})"
        embed = discord.Embed(
            color=COLOR_CODE,
            title=get_lan(interaction.user.id, "music_now_playing"),
            description=song,
        )

        embed.add_field(
            name=get_lan(interaction.user.id, "music_shuffle"),
            value=(
                get_lan(interaction.user.id, "music_shuffle_already_on")
                if player.shuffle
                else get_lan(interaction.user.id, "music_shuffle_already_off")
            ),
            inline=True,
        )
        embed.add_field(
            name=get_lan(interaction.user.id, "music_repeat"),
            value=[
                get_lan(interaction.user.id, "music_repeat_already_off"),
                get_lan(interaction.user.id, "music_repeat_already_one"),
                get_lan(interaction.user.id, "music_repeat_already_on"),
            ][player.loop],
            inline=True,
        )

        embed.set_thumbnail(
            url=f"{player.current.uri.replace('https://www.youtube.com/watch?v=', 'http://img.youtube.com/vi/')}/0.jpg"
        )
        embed.set_footer(text=BOT_NAME_TAG_VER)
        await interaction.followup.send(embed=embed)


    @app_commands.command(name="queue", description="Send music queue!")
    @app_commands.check(create_player)
    async def queue(self, interaction: discord.Interaction):
        await interaction.response.defer()

        try:
            player = self.bot.lavalink.player_manager.get(interaction.guild.id)
            if not player.queue:
                embed = discord.Embed(
                    title=get_lan(interaction.user.id, "music_no_music_in_the_playlist"),
                    description="",
                    color=COLOR_CODE,
                )
                embed.set_footer(text=BOT_NAME_TAG_VER)
                return await interaction.followup.send(embed=embed)

            items_per_page = 10
            pages = [
                player.queue[i : i + items_per_page]
                for i in range(0, len(player.queue), items_per_page)
            ]

            class QueuePaginator(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=60)
                    self.current_page = 0

                @discord.ui.button(label="Previous", style=discord.ButtonStyle.gray)
                async def previous_page(
                    self, button_interaction: discord.Interaction, button: discord.ui.Button
                ):
                    self.current_page = (self.current_page - 1) % len(pages)
                    await self.update_message(button_interaction)

                @discord.ui.button(label="Next", style=discord.ButtonStyle.gray)
                async def next_page(
                    self, button_interaction: discord.Interaction, button: discord.ui.Button
                ):
                    self.current_page = (self.current_page + 1) % len(pages)
                    await self.update_message(button_interaction)

                async def update_message(self, button_interaction: discord.Interaction):
                    queue_list = ""
                    start_index = self.current_page * items_per_page
                    for index, track in enumerate(
                        pages[self.current_page], start=start_index + 1
                    ):
                        queue_list += f"`{index}.` [**{track.title}**]({track.uri})\n"
                    embed = discord.Embed(
                        description=get_lan(button_interaction.user.id, "music_q").format(
                            lenQ=len(player.queue), queue_list=queue_list
                        ),
                        color=COLOR_CODE,
                    )
                    embed.set_footer(
                        text=f"{get_lan(button_interaction.user.id, 'music_page')} {self.current_page + 1}/{len(pages)}\n{BOT_NAME_TAG_VER}"
                    )
                    await button_interaction.response.edit_message(embed=embed, view=self)

            view = QueuePaginator()
            queue_list = ""
            for index, track in enumerate(pages[0], start=1):
                queue_list += f"`{index}.` [**{track.title}**]({track.uri})\n"
            embed = discord.Embed(
                description=get_lan(interaction.user.id, "music_q").format(
                    lenQ=len(player.queue), queue_list=queue_list
                ),
                color=COLOR_CODE,
            )
            embed.set_footer(
                text=f"{get_lan(interaction.user.id, 'music_page')} 1/{len(pages)}\n{BOT_NAME_TAG_VER}"
            )
            await interaction.followup.send(embed=embed, view=view)

        except Exception as e:
            error_embed = discord.Embed(
                title="Error",
                description=f"An error occurred while fetching the queue: {str(e)}",
                color=discord.Color.red(),
            )
            error_embed.set_footer(text=BOT_NAME_TAG_VER)
            await interaction.followup.send(embed=error_embed)

    @app_commands.command(
        name="repeat", description="Repeat one song or repeat multiple songs!"
    )
    @app_commands.check(create_player)
    async def repeat(self, interaction: discord.Interaction):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        if not player.is_playing:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_not_playing"),
                description="",
                color=COLOR_CODE,
            )
            embed.set_footer(text=BOT_NAME_TAG_VER)
            return await interaction.followup.send(embed=embed)

        if player.loop == 0:
            player.set_loop(2)
        elif player.loop == 2:
            player.set_loop(1)
        else:
            player.set_loop(0)

        Database().set_loop(interaction.guild.id, player.loop)

        embed = None
        if player.loop == 0:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_repeat_off"),
                description="",
                color=COLOR_CODE,
            )
        elif player.loop == 1:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_repeat_one"),
                description="",
                color=COLOR_CODE,
            )
        elif player.loop == 2:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_repeat_all"),
                description="",
                color=COLOR_CODE,
            )
        if embed is not None:
            embed.set_footer(text=BOT_NAME_TAG_VER)
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="remove", description="Remove music from the playlist!")
    @app_commands.describe(
        index="Queue에서 제거하고 싶은 음악이 몇 번째 음악인지 입력해 주세요"
    )
    @app_commands.check(create_player)
    async def remove(self, interaction: discord.Interaction, index: int):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        if not player.queue:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_remove_no_wating_music"),
                description="",
                color=COLOR_CODE,
            )
            embed.set_footer(text=BOT_NAME_TAG_VER)
            return await interaction.followup.send(embed=embed)
        if index > len(player.queue) or index < 1:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_remove_input_over").format(
                    last_queue=len(player.queue)
                ),
                description="",
                color=COLOR_CODE,
            )
            embed.set_footer(text=BOT_NAME_TAG_VER)
            return await interaction.followup.send(embed=embed)
        removed = player.queue.pop(index - 1)  # Account for 0-index.
        embed = discord.Embed(
            title=get_lan(interaction.user.id, "music_remove_form_playlist").format(
                remove_music=removed.title
            ),
            description="",
            color=COLOR_CODE,
        )
        embed.set_footer(text=BOT_NAME_TAG_VER)
        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="shuffle",
        description="The music in the playlist comes out randomly from the next song!",
    )
    @app_commands.check(create_player)
    async def shuffle(self, interaction: discord.Interaction):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        if not player.is_playing:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_not_playing"),
                description="",
                color=COLOR_CODE,
            )
            embed.set_footer(text=BOT_NAME_TAG_VER)
            return await interaction.followup.send(embed=embed)

        player.set_shuffle(not player.shuffle)

        Database().set_shuffle(interaction.guild.id, player.shuffle)

        if player.shuffle:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_shuffle_on"),
                description="",
                color=COLOR_CODE,
            )
        else:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_shuffle_off"),
                description="",
                color=COLOR_CODE,
            )
        embed.set_footer(text=BOT_NAME_TAG_VER)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="volume", description="Changes or display the volume")
    @app_commands.describe(volume="볼륨값을 입력하세요")
    @app_commands.check(create_player)
    async def volume(self, interaction: discord.Interaction, volume: int = None):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        if volume is None:
            volicon = await volumeicon(player.volume)
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_now_vol").format(
                    volicon=volicon, volume=player.volume
                ),
                description="",
                color=COLOR_CODE,
            )
            embed.set_footer(text=BOT_NAME_TAG_VER)
            return await interaction.followup.send(embed=embed)
        if volume > 1000 or volume < 1:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_input_over_vol"),
                description=get_lan(interaction.user.id, "music_default_vol"),
                color=COLOR_CODE,
            )
            embed.set_footer(text=BOT_NAME_TAG_VER)
            return await interaction.followup.send(embed=embed)

        await player.set_volume(volume)

        volicon = await volumeicon(player.volume)
        embed = discord.Embed(
            title=get_lan(interaction.user.id, "music_set_vol").format(
                volicon=volicon, volume=player.volume
            ),
            description="",
            color=COLOR_CODE,
        )
        embed.set_footer(text=BOT_NAME_TAG_VER)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="pause", description="Pause or resume music!")
    @app_commands.check(create_player)
    async def pause(self, interaction: discord.Interaction):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        if not player.is_playing:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_not_playing"),
                description="",
                color=COLOR_CODE,
            )
            embed.set_footer(text=BOT_NAME_TAG_VER)
            return await interaction.followup.send(embed=embed)
        if player.paused:
            await player.set_pause(False)
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_resume"),
                description="",
                color=COLOR_CODE,
            )
            embed.set_footer(text=BOT_NAME_TAG_VER)
            await interaction.followup.send(embed=embed)
        else:
            await player.set_pause(True)
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_pause"),
                description="",
                color=COLOR_CODE,
            )
            embed.set_footer(text=BOT_NAME_TAG_VER)
            await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="seek",
        description="Adjust the music play time in seconds by the number after the command!",
    )
    @app_commands.describe(seconds="이동할 초를 입력하세요")
    async def seek(self, interaction: discord.Interaction, seconds: int):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        track_time = player.position + (seconds * 1000)
        await player.seek(track_time)
        embed = discord.Embed(
            title=get_lan(interaction.user.id, "music_seek_move_to").format(
                move_time=lavalink.utils.format_time(track_time)
            ),
            description="",
            color=COLOR_CODE,
        )
        embed.set_footer(text=BOT_NAME_TAG_VER)
        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="chartplay",
        description="Add the top songs on the selected chart to your playlist!",
    )
    @app_commands.describe(
        chart="Choose chart", count="Enter the number of chart songs to play"
    )
    @app_commands.choices(
        chart=[
            app_commands.Choice(name="Melon", value="MELON"),
            app_commands.Choice(name="Billboard", value="BILLBOARD"),
            app_commands.Choice(name="Billboard Japan", value="BILLBOARD JAPAN"),
        ]
    )
    @app_commands.check(create_player)
    async def chartplay(
        self, interaction: discord.Interaction, chart: str, count: int = 10
    ):
        await interaction.response.defer()

        embed = None
        artist = None
        title = None
        playmsg = None

        count = max(1, min(count, 100))

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        if chart == "MELON":
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_parsing_melon"),
                color=COLOR_CODE,
            )
            embed.set_footer(text=BOT_NAME_TAG_VER)
            playmsg = await interaction.followup.send(embed=embed)
            title, artist = await get_melon(count)
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_melon_chart_play"),
                color=COLOR_CODE,
            )
        elif chart == "BILLBOARD":
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_parsing_billboard"),
                color=COLOR_CODE,
            )
            embed.set_footer(text=BOT_NAME_TAG_VER)
            playmsg = await interaction.followup.send(embed=embed)
            title, artist = await get_billboard(count)
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_billboard_chart_play"),
                color=COLOR_CODE,
            )
        elif chart == "BILLBOARD JAPAN":
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_parsing_billboardjp"),
                color=COLOR_CODE,
            )
            embed.set_footer(text=BOT_NAME_TAG_VER)
            playmsg = await interaction.followup.send(embed=embed)
            title, artist = await get_billboardjp(count)
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_billboardjp_chart_play"),
                color=COLOR_CODE,
            )

        musics = [
            f"{artist[i]} {title[i]}"
            for i in range(count)
            if artist is not None and title is not None
        ]

        playmsg, player, thumbnail, playmusic, passmusic = await play_list(
            player, interaction, musics, playmsg
        )

        if embed is not None:
            embed.add_field(
                name=get_lan(interaction.user.id, "music_played_music"),
                value=playmusic,
                inline=False,
            )
            embed.add_field(
                name=get_lan(interaction.user.id, "music_can_not_find_music"),
                value=passmusic,
                inline=False,
            )
            if thumbnail is not None:
                embed.set_thumbnail(url=f"http://img.youtube.com/vi/{thumbnail}/0.jpg")
            embed.set_footer(text=BOT_NAME_TAG_VER)
            await playmsg.edit(embed=embed)
            if not player.is_playing:
                await player.play()

    @app_commands.command(
        name="list", description="Load playlists or play the music from that playlist!"
    )
    @app_commands.describe(arg="재생할 플레이리스트의 제목을 입력해 주세요")
    @app_commands.check(create_player)
    async def list(self, interaction: discord.Interaction, arg: str = None):
        await interaction.response.defer()

        anilistpath = "musicbot/anilist"

        files = [
            file.replace(".txt", "")
            for file in os.listdir(anilistpath)
            if file.endswith(".txt")
        ]
        files = sorted(files)

        if arg == "-a":
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_len_list").format(
                    files_len=len(files)
                ),
                description=get_lan(interaction.user.id, "music_len_list").format(
                    files_len=len(files)
                ),
                color=COLOR_CODE,
            )
            embed.set_footer(text=BOT_NAME_TAG_VER)
            return await interaction.followup.send(embed=embed)

        if arg is not None:
            try:
                if arg not in files:
                    arg = difflib.get_close_matches(arg, files, 1, 0.65)[0]
                    if arg is None:
                        raise Exception("Can't find music")

                with open(f"{anilistpath}/{arg}.txt", "r") as f:
                    list_str = f.read()

            except Exception:
                embed = discord.Embed(
                    title=get_lan(interaction.user.id, "music_list_can_not_find"),
                    description=arg,
                    color=COLOR_CODE,
                )
                embed.set_footer(text=BOT_NAME_TAG_VER)
                return await interaction.followup.send(embed=embed)

            player = self.bot.lavalink.player_manager.get(interaction.guild.id)
            music_list = [music for music in list_str.split("\n") if music]

            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_list_finding"),
                color=COLOR_CODE,
            )
            embed.set_footer(text=BOT_NAME_TAG_VER)
            playmsg = await interaction.followup.send(embed=embed)

            playmsg, player, thumbnail, playmusic, passmusic = await play_list(
                player, interaction, music_list, playmsg
            )

            embed = discord.Embed(
                title=f":arrow_forward: | {arg}", description="", color=COLOR_CODE
            )
            embed.add_field(
                name=get_lan(interaction.user.id, "music_played_music"),
                value=playmusic,
                inline=False,
            )
            embed.add_field(
                name=get_lan(interaction.user.id, "music_can_not_find_music"),
                value=passmusic,
                inline=False,
            )
            if thumbnail is not None:
                embed.set_thumbnail(url=f"http://img.youtube.com/vi/{thumbnail}/0.jpg")
            embed.set_footer(text=BOT_NAME_TAG_VER)
            await playmsg.edit(embed=embed)
            if not player.is_playing:
                await player.play()

        else:
            page = 15
            if len(files) <= page:
                embed = discord.Embed(
                    title=get_lan(interaction.user.id, "music_playlist_list"),
                    description="\n".join(files),
                    color=COLOR_CODE,
                )
                embed.set_footer(text=BOT_NAME_TAG_VER)
                return await interaction.followup.send(embed=embed)

            class PlaylistPaginator(discord.ui.View):
                def __init__(self, pages):
                    super().__init__()
                    self.pages = pages
                    self.current_page = 0

                @discord.ui.button(label="Previous", style=discord.ButtonStyle.gray)
                async def previous_page(
                    self, interaction: discord.Interaction, button: discord.ui.Button
                ):
                    self.current_page = (self.current_page - 1) % len(self.pages)
                    await self.update_message(interaction)

                @discord.ui.button(label="Next", style=discord.ButtonStyle.gray)
                async def next_page(
                    self, interaction: discord.Interaction, button: discord.ui.Button
                ):
                    self.current_page = (self.current_page + 1) % len(self.pages)
                    await self.update_message(interaction)

                async def update_message(self, interaction: discord.Interaction):
                    embed = discord.Embed(
                        title=get_lan(interaction.user.id, "music_playlist_list"),
                        description="\n".join(self.pages[self.current_page]),
                        color=COLOR_CODE,
                    )
                    embed.set_footer(
                        text=f"{get_lan(interaction.user.id, 'music_page')} {self.current_page + 1}/{len(self.pages)}\n{BOT_NAME_TAG_VER}"
                    )
                    await interaction.response.edit_message(embed=embed, view=self)

            pages = [files[i : i + page] for i in range(0, len(files), page)]
            view = PlaylistPaginator(pages)
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "music_playlist_list"),
                description="\n".join(pages[0]),
                color=COLOR_CODE,
            )
            embed.set_footer(
                text=f"{get_lan(interaction.user.id, 'music_page')} 1/{len(pages)}\n{BOT_NAME_TAG_VER}"
            )
            await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(name="equalizer", description="Send equalizer dashboard")
    @app_commands.check(create_player)
    async def equalizer(self, interaction: discord.Interaction):
        await interaction.response.defer()

        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        eq = player.fetch("eq", Equalizer())

        selector = f'{" " * 8}^^^'
        await interaction.followup.send(
            f"```diff\n{eq.visualise()}\n{selector}```",
            view=EqualizerButton(interaction, player, eq, 0),
        )


async def setup(bot):
    await bot.add_cog(Music(bot))
    LOGGER.info("Music loaded!")

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
            placeholder=get_lan(interaction.user.id, "music_search_select_placeholder"),
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
        super().__init__()
        self.add_item(SearchSelect(tracks, cog, interaction))

