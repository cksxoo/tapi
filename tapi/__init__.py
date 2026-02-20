import os
import sys
import logging


# Bot version
BOT_VER = "v0.9.1"

# enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

LOGGER = logging.getLogger(__name__)

# if version < 3.11, stop bot.
if sys.version_info[0] < 3 or sys.version_info[1] < 10:
    LOGGER.error(
        "3.11 버전 이상의 Python 이 있어야 합니다. 여러 기능이 Python3.11 버전을 따릅니다. 봇 종료."
    )
    quit(1)


from tapi.config import Development as Config

TOKEN = Config.TOKEN
OWNERS = Config.OWNERS
DEBUG_SERVER = Config.DEBUG_SERVER
APPLICATION_NAME = Config.APPLICATION_NAME
APP_TAG = Config.APP_TAG
CLIENT_ID = Config.CLIENT_ID
THEME_COLOR = Config.THEME_COLOR
IDLE_COLOR = Config.IDLE_COLOR
SUCCESS_COLOR = Config.SUCCESS_COLOR
ERROR_COLOR = Config.ERROR_COLOR
WARNING_COLOR = Config.WARNING_COLOR
INFO_COLOR = Config.INFO_COLOR
MUSIC_COLOR = Config.MUSIC_COLOR
APP_DESCRIPTION = Config.APP_DESCRIPTION
HOST = Config.HOST
PSW = Config.PSW
REGION = Config.REGION
PORT = Config.PORT
LAVALINK_AUTO_UPDATE = Config.LAVALINK_AUTO_UPDATE
LAVALINK_PLUGINS = Config.LAVALINK_PLUGINS
# SQL settings removed - using Supabase only

KOREANBOT_TOKEN = Config.KOREANBOT_TOKEN
TOPGG_TOKEN = Config.TOPGG_TOKEN

# SQLite database settings removed - using Supabase only

EXTENSIONS = []
# Exclude utility modules that are not Discord extensions
EXCLUDED_MODULES = {
    "audio_connection",
    "music_handlers",
    "music_views",
    "player_backup",
}
for file in os.listdir("tapi/modules"):
    if file.endswith(".py"):
        module_name = file.replace(".py", "")
        if module_name not in EXCLUDED_MODULES:
            EXTENSIONS.append(module_name)

APP_BANNER_URL = (
    "https://raw.githubusercontent.com/cksxoo/tapi/main/docs/themes/2026-main/discord.png?v=20260220"
)
APP_NAME_TAG_VER = "%s%s | %s" % (APPLICATION_NAME, APP_TAG, BOT_VER)

# Initialize database after all imports are complete
from tapi.utils.database import Database

Database().create_table()
