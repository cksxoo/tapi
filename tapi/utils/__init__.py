"""
Utility functions and classes for the music bot.
"""

from .database import Database
from .statistics import Statistics
from .language import get_lan
from .redis_manager import RedisManager, redis_manager

# Volume icon utility function
async def volumeicon(vol: int) -> str:
    """
    Get volume icon based on volume level.
    
    Args:
        vol: Volume level (0-100)
        
    Returns:
        Discord emoji string for the volume level
    """
    vol_icon = ":loud_sound:"
    if 1 <= vol <= 10:
        vol_icon = ":mute:"
    elif 11 <= vol <= 30:
        vol_icon = ":speaker:"
    elif 31 <= vol <= 70:
        vol_icon = ":sound:"
    return vol_icon

__all__ = [
    'Database',
    'Statistics', 
    'get_lan',
    'RedisManager',
    'redis_manager',
    'volumeicon'
]