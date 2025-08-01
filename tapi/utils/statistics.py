from datetime import datetime
import pytz
from tapi.utils.database import Database
from tapi.config import Development as Config
from tapi import LOGGER


class Statistics:
    """Statistics tracking class for music bot."""
    
    def __init__(self):
        self.database = Database()
        # 설정 파일에서 시간대를 가져오거나 기본값 사용
        self.timezone = getattr(Config, 'TIMEZONE', 'Asia/Seoul')
    
    def record_play(self, track, guild_id, channel_id, user_id, success=True, interaction=None):
        """
        Record a play attempt in the statistics database.
        
        Args:
            track: The lavalink track object (can be None for failed attempts)
            guild_id: Discord guild ID
            channel_id: Discord channel ID  
            user_id: Discord user ID
            success: Whether the play attempt was successful
            interaction: Discord interaction object (optional, used to get names)
        """
        try:
            # Get current date and time in configured timezone
            tz = pytz.timezone(self.timezone)
            now = datetime.now(tz)
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")
            
            # Extract track information if available
            if track:
                video_id = getattr(track, 'identifier', '') or ''
                title = getattr(track, 'title', 'Unknown') or 'Unknown'
                artist = getattr(track, 'author', 'Unknown') or 'Unknown'
                # Convert duration from milliseconds to seconds
                duration_ms = getattr(track, 'duration', 0) or 0
                duration = duration_ms // 1000
            else:
                video_id = ''
                title = 'Failed Play Attempt'
                artist = 'Unknown'
                duration = 0
            
            # Get guild, channel, and user information
            if interaction:
                # Try to get actual names from the interaction
                guild_name = interaction.guild.name if interaction.guild else str(guild_id)
                channel_name = interaction.channel.name if hasattr(interaction.channel, 'name') else str(channel_id)
                user_name = interaction.user.display_name if interaction.user else str(user_id)
            else:
                # Fallback to IDs if no interaction provided
                guild_name = str(guild_id)
                channel_name = str(channel_id)
                user_name = str(user_id)
            
            # created_at을 설정된 시간대로 설정
            created_at = now.strftime("%Y-%m-%d %H:%M:%S")
            
            # Record in database
            self.database.set_statistics(
                date=date_str,
                time=time_str,
                guild_id=str(guild_id),
                guild_name=guild_name,
                channel_id=str(channel_id),
                channel_name=channel_name,
                user_id=str(user_id),
                user_name=user_name,
                video_id=video_id,
                title=title,
                artist=artist,
                duration=duration,
                success=success,
                created_at=created_at,
            )
            
        except Exception as e:
            LOGGER.error(f"Error recording statistics: {e}")
