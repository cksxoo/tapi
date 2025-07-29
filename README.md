# TAPI Bot

## About
TAPI Bot is a modern Discord music bot built with Python and discord.py. It features high-quality audio streaming through Lavalink and supports various music sources.

## Features
- 🎵 High-quality music playback with Lavalink
- 🔀 Queue management with shuffle and repeat modes
- 📱 Slash command support
- 🌐 Multi-language support (Korean/English)
- 🎛️ Volume control and audio effects
- 📊 Music statistics tracking
- 🔄 Redis-based session management
- 🐳 Docker containerization with sharding support

## Project Structure
```
tapi/
├── modules/          # Bot command modules
│   ├── player.py    # Music player commands
│   ├── admin.py     # Administrator commands
│   ├── info.py      # Bot information
│   └── ...
├── utils/           # Utility functions
├── config.py        # Bot configuration
└── __main__.py      # Bot entry point
```

## Installation
1. Clone the repository
2. Copy `tapi/sample_config.py` to `tapi/config.py`
3. Configure your bot token and settings
4. Run with Docker: `docker-compose up`

## Configuration
Edit `tapi/config.py` with your settings:
- `TOKEN`: Your Discord bot token
- `APPLICATION_NAME`: Your bot's display name
- `CLIENT_ID`: Your Discord application ID
- `THEME_COLOR`: Bot embed color

## Commands
- `/play <query>` - Play music from YouTube or URL
- `/queue` - Show current music queue
- `/skip` - Skip current track
- `/volume <0-1000>` - Adjust playback volume
- `/disconnect` - Disconnect from voice channel

## Tech Stack
- **Python 3.11+** with discord.py
- **Lavalink** for audio processing
- **Redis** for session management
- **Docker** for containerization
- **PostgreSQL/MySQL** for data persistence

---

<img width="1536" height="1024" alt="image" src="https://github.com/leechanwoo-kor/music_bot/blob/main/docs/banner.png?raw=true" />