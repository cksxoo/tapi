import yt_dlp
import asyncio
from async_timeout import timeout
import discord
from discord import app_commands
from discord.ext import commands
import re


class YTDLPSource:
    YTDLP_OPTIONS = {
        "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio",
        "format_sort": [
            "acodec:opus",
            "asr:48000",
            "abr:192",
        ],
        "extractaudio": True,
        "audioformat": "opus",
        "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
        "restrictfilenames": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "ignoreerrors": False,
        "logtostderr": False,
        "quiet": True,
        "no_warnings": True,
        "default_search": "auto",
        "source_address": "0.0.0.0",
        "buffersize": 32768,
    }

    def __init__(
        self, ctx: commands.Context, source: discord.FFmpegPCMAudio, *, data: dict
    ):
        self.requester = ctx.author
        self.channel = ctx.channel
        self.data = data
        self.source = source
        self.title = data.get("title", "Unknown title")
        self.url = data.get("webpage_url", "Unknown URL")
        self.duration = self.parse_duration(data.get("duration", 0))
        self.volume = 0.5

    @staticmethod
    def parse_duration(duration):
        if duration == 0:
            return "LIVE"
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    @classmethod
    async def create_source(
        cls, ctx: commands.Context, search: str, *, loop: asyncio.BaseEventLoop = None
    ):
        loop = loop or asyncio.get_event_loop()

        with yt_dlp.YoutubeDL(cls.YTDLP_OPTIONS) as ydl:
            try:
                if re.match(r"https?://(?:www\.)?.+", search):
                    data = await loop.run_in_executor(
                        None, lambda: ydl.extract_info(search, download=False)
                    )
                else:
                    data = await loop.run_in_executor(
                        None,
                        lambda: ydl.extract_info(f"ytsearch:{search}", download=False),
                    )

                if "entries" in data:
                    data = data["entries"][0]

                url = data["url"]

                # FFmpeg 옵션 수정
                ffmpeg_options = {
                    "before_options": (
                        "-reconnect 1 "
                        "-reconnect_streamed 1 "
                        "-reconnect_delay_max 5"
                    ),
                    "options": (
                        "-vn "  # 비디오 비활성화
                        "-acodec libopus "  # Opus 코덱 사용
                        "-ar 48000 "  # 샘플레이트
                        "-ac 2 "  # 스테레오
                        "-b:a 192k "  # 비트레이트
                        "-loglevel error"  # 에러 로그만 표시
                    ),
                }

                source = discord.FFmpegPCMAudio(url, **ffmpeg_options)
                return cls(ctx, source, data=data)

            except Exception as e:
                raise e

    def cleanup(self):
        """Clean up the audio source."""
        try:
            if hasattr(self, "source"):
                if hasattr(self.source, "process"):
                    try:
                        self.source.process.kill()
                    except Exception:
                        pass
                if hasattr(self.source, "cleanup"):
                    try:
                        self.source.cleanup()
                    except Exception:
                        pass
        except Exception:
            pass


class MusicPlayer:
    def __init__(self, ctx):
        self.bot = ctx.bot
        self.guild = ctx.guild
        self.channel = ctx.channel
        self.queue = asyncio.Queue()
        self.next = asyncio.Event()
        self.current = None
        self.volume = 0.5
        self.loop = False
        self._stopped = False

        ctx.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        while not self._stopped:
            self.next.clear()

            try:
                async with timeout(180):  # 3 minutes
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                return await self.destroy()

            if not isinstance(source, YTDLPSource):
                continue

            # Create a new PCMVolumeTransformer for the source
            try:
                transformed_source = discord.PCMVolumeTransformer(
                    source.source, volume=self.volume
                )
                source.source = transformed_source
                self.current = source

                def after_playing(error):
                    if error:
                        print(f"Player error: {error}")
                    self.bot.loop.call_soon_threadsafe(self.next.set)

                self.guild.voice_client.play(source.source, after=after_playing)

                embed = discord.Embed(
                    title="Now Playing 🎵",
                    description=f"[{source.title}]({source.url})",
                    color=discord.Color.green(),
                )
                embed.add_field(name="Duration", value=source.duration)
                embed.add_field(name="Quality", value="High Quality (192kbps)")
                embed.add_field(name="Requested by", value=source.requester.name)

                await self.channel.send(embed=embed)

                await self.next.wait()

                # Clean up the source properly
                if self.current:
                    try:
                        self.current.cleanup()
                    except Exception:
                        pass
                    self.current = None

                if self.loop and not self._stopped:
                    await self.queue.put(source)

            except Exception as e:
                print(f"Player error: {e}")
                continue

    async def destroy(self):
        """Disconnect and cleanup the player."""
        self._stopped = True

        try:
            if self.current:
                self.current.cleanup()

            while True:
                try:
                    item = self.queue.get_nowait()
                    if hasattr(item, "cleanup"):
                        item.cleanup()
                except asyncio.QueueEmpty:
                    break

            if self.guild.voice_client:
                await self.guild.voice_client.disconnect(force=True)
        except Exception:
            pass

        try:
            del self.bot.cog_YTMusicCommands.players[self.guild.id]
        except Exception:
            pass


class YTMusicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players = {}

    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You need to be in a voice channel to use this command.")
                raise commands.CommandError("Author not connected to a voice channel.")
        return True

    @app_commands.command(name="ytplay", description="Play music using yt-dlp")
    async def play(self, interaction: discord.Interaction, *, search: str):
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)

        try:
            await self.ensure_voice(ctx)

            player = self.players.get(ctx.guild.id)
            if not player:
                player = MusicPlayer(ctx)
                self.players[ctx.guild.id] = player

            source = await YTDLPSource.create_source(ctx, search, loop=self.bot.loop)
            await player.queue.put(source)

            embed = discord.Embed(
                title="Added to Queue 🎵",
                description=f"[{source.title}]({source.url})",
                color=discord.Color.blue(),
            )
            embed.add_field(name="Duration", value=source.duration)
            embed.add_field(name="Requested by", value=ctx.author.name)

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}")

    @app_commands.command(name="ytvolume", description="Change the volume (0-200)")
    async def volume(self, interaction: discord.Interaction, volume: int):
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)

        if not 0 <= volume <= 200:
            return await interaction.followup.send("Volume must be between 0 and 200")

        player = self.players.get(ctx.guild.id)
        if not player:
            return await interaction.followup.send("No music is playing.")

        await player.set_volume(volume / 100)
        await interaction.followup.send(f"🔊 Volume set to {volume}%")

    @app_commands.command(
        name="ytstop", description="Stop the music and clear the queue"
    )
    async def stop(self, interaction: discord.Interaction):
        ctx = await commands.Context.from_interaction(interaction)

        player = self.players.pop(ctx.guild.id, None)
        if player:
            await player.destroy()
            await interaction.response.send_message(
                "⏹ Stopped the music and disconnected."
            )
        else:
            await interaction.response.send_message("Not playing any music right now.")


async def setup(bot):
    await bot.add_cog(YTMusicCommands(bot))
