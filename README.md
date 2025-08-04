# 🎵 TAPI Bot

> **OMG! 안녕하세요! ヾ(｡>﹏<｡)ﾉﾞ✧** A cute and friendly Discord music bot that brings joy to your server! ✧(≧◡≦) ♡

## ✨ About
TAPI is a modern Discord music bot built with Python and discord.py. Designed with a cute and friendly personality, it delivers high-quality audio streaming through Lavalink while being easy and fun to use!

## 🌟 Features
- 🎵 **High-quality music playback** with Lavalink integration
- 🔀 **Smart queue management** with shuffle and repeat modes
- 📱 **Interactive slash commands** with button-based help system
- 🌐 **Multi-language support** (Korean/English) with cute messages
- 🎛️ **Volume control** (1-100% for safe listening)
- 📊 **Redis-powered monitoring** with web dashboard
- 🐳 **Docker containerization** with sharding support
- 💝 **Auto-disappearing messages** to keep channels clean
- 🎀 **Kawaii personality** with adorable responses

## 🎯 Music Commands
### 🎮 Playback Control
- `/connect` - Connect to voice channel
- `/play [song/link]` - Play music from various sources
- `/pause` - Pause/resume playback
- `/skip` - Skip to next song
- `/disconnect` - Leave voice channel

### 🔊 Volume & Queue
- `/volume [1-100]` - Adjust volume (safe maximum!)
- `/queue` - Check current queue
- `/shuffle` - Toggle shuffle mode
- `/repeat` - Toggle repeat mode

### ⚙️ Advanced Features
- `/nowplaying` - Current song information
- `/remove [number]` - Remove song from queue

## 🌍 General Commands
- `/help` - Interactive help menu with cute personality
- `/invite` - Invite bot to other servers
- `/language` - Switch between Korean/English

## 🏗️ Project Structure
```
tapi/
├── modules/          # Bot command modules
│   ├── player.py     # Music player commands
│   ├── help.py       # Interactive help system
│   └── other.py      # General commands & language management
├── utils/            # Utility functions
│   ├── language.py   # Multi-language support
│   ├── redis_manager.py # Redis integration
│   └── send_temp_message.py # Auto-disappearing messages
├── languages/        # Language packs
│   ├── ko.json       # Korean messages
│   └── en.json       # English messages
├── sample_config.py  # Configuration template
└── __main__.py       # Bot entry point with sharding
```

## 🚀 Installation & Setup

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Lavalink server
- Redis server (optional, for monitoring)

### Quick Start
1. **Clone the repository**
   ```bash
   git clone https://github.com/cksxoo/tapi.git
   cd tapi
   ```

2. **Configure the bot**
   ```bash
   cp tapi/sample_config.py tapi/config.py
   # Edit config.py with your bot token and settings
   ```

3. **Run with Docker**
   ```bash
   docker-compose up -d
   ```

### Configuration Options
Edit `tapi/config.py`:
- `TOKEN`: Your Discord bot token
- `APPLICATION_NAME`: Bot display name
- `CLIENT_ID`: Discord application ID
- `THEME_COLOR`: Embed color (default: cute theme)
- `HOST/PORT/PSW`: Lavalink server settings

## 🎨 Personality & Design
TAPI Bot features a unique kawaii personality with:
- 💕 Cute Japanese emoticons and expressions
- 🌸 Friendly and encouraging messages
- 🎀 Auto-disappearing responses to keep chats clean
- ✨ Interactive help system with buttons
- 🌈 Consistent cute theming throughout

## 🛠️ Tech Stack
- **Python 3.11+** with discord.py 2.0+
- **Lavalink** for high-quality audio processing
- **Redis** for session management & monitoring
- **Docker** for easy deployment
- **Interactive UI** with Discord buttons and views

## 📊 Monitoring
Includes Redis-based monitoring system with:
- Real-time shard status tracking
- Memory and CPU usage monitoring
- Active player statistics
- Web dashboard integration ready

## 🤝 Contributing
We welcome contributions! Please feel free to submit issues and pull requests to make TAPI even cuter and more functional! ♡(˃͈ દ ˂͈ ༶ )

## 📝 License
This project is open source. Feel free to use and modify while keeping the cute spirit alive! ✧(≧◡≦)

---

**Made with 💖 and lots of ✨ kawaii energy ✨**

---

<img width="1536" height="1024" alt="image" src="https://github.com/leechanwoo-kor/music_bot/blob/main/docs/banner.png?raw=true" />