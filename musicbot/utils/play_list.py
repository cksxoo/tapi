import re
import discord
import lavalink

from musicbot.utils.language import get_lan
from musicbot.utils.statistics import Statistics
from musicbot import COLOR_CODE

url_rx = re.compile(r'https?://(?:www\.)?.+')

async def play_list(player, interaction: discord.Interaction, musics: list, playmsg):
    """ 음악 리스트의 음악 재생 """
    trackcount = 0
    playmusic = get_lan(interaction.user.id, "music_none")
    passmusic = get_lan(interaction.user.id, "music_none")
    loading_dot_count = 0
    thumbnail = None

    for music in musics:
        loading_dot = "." * (loading_dot_count % 3 + 1)
        loading_dot_count += 1

        embed = discord.Embed(
            title=get_lan(interaction.user.id, "music_adding_music").format(loading_dot=loading_dot),
            description=music,
            color=COLOR_CODE
        )
        await playmsg.edit(embed=embed)
        
        query = music if url_rx.match(music) else f'ytsearch:{music}'
        
        try:
            results = await player.node.get_tracks(query)
            if not results or not results.tracks:
                if passmusic == get_lan(interaction.user.id, "music_none"):
                    passmusic = music
                else:
                    passmusic = f"{passmusic}\n{music}"
                continue

            track = results.tracks[0]

            # Music statistical
            Statistics().up(track.identifier)

            if playmusic == get_lan(interaction.user.id, "music_none"):
                playmusic = music
            else:
                playmusic = f"{playmusic}\n{music}"
            
            if not thumbnail:
                thumbnail = track.identifier

            # Add the track directly without using lavalink.models.AudioTrack
            player.add(requester=interaction.user.id, track=track)

            if not player.is_playing:
                await player.play()

        except Exception as e:
            print(f"Error adding track {music}: {e}")
            if passmusic == get_lan(interaction.user.id, "music_none"):
                passmusic = music
            else:
                passmusic = f"{passmusic}\n{music}"

    return playmsg, player, thumbnail, playmusic, passmusic