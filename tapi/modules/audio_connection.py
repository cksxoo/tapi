import discord
import lavalink
from tapi import (
    LOGGER,
    HOST,
    PSW,
    REGION,
    PORT,
)


class AudioConnection(discord.VoiceClient):
    """
    This is the preferred way to handle external voice sending
    This client will be created via a cls in the connect method of the channel
    see the following documentation:
    https://discordpy.readthedocs.io/en/latest/api.html#voiceprotocol
    """

    def __init__(self, client: discord.Client, channel: discord.abc.Connectable):
        discord.VoiceProtocol.__init__(self, client, channel)
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

    def is_connected(self) -> bool:
        """Lavalink player 상태로 연결 여부 확인 (_connection 우회)."""
        player = self.lavalink.player_manager.get(self.guild_id)
        return player is not None and player.is_connected

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

        # 웹 대시보드에 disconnect 상태 전파
        try:
            from tapi.utils.redis_manager import redis_manager
            await redis_manager.publish_player_update(self.guild_id, "disconnect", {
                "guild_id": str(self.guild_id),
                "is_connected": False,
                "is_playing": False,
                "is_paused": False,
                "current_track": None,
                "queue": [],
                "queue_length": 0,
                "volume": 100,
                "loop": 0,
                "shuffle": False,
                "channel_name": "",
            })
        except Exception as e:
            LOGGER.debug(f"Failed to publish disconnect state: {e}")

        # 음악 메시지 정리 (Music Cog에서 접근)
        try:
            music_cog = self.client.get_cog("Music")
            if music_cog:
                await music_cog._cleanup_music_message(self.guild_id, "destroy")
        except Exception as e:
            LOGGER.error(f"Error cleaning up music message in _destroy: {e}")

        try:
            await self.lavalink.player_manager.destroy(self.guild_id)
        except lavalink.errors.ClientError:
            pass
