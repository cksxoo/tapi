import os
import sys
import logging

from musicbot.utils.database import Database


# Bot version
BOT_VER = "v0.6.2"

# enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

LOGGER = logging.getLogger(__name__)

# if version < 3.11, stop bot.
if sys.version_info[0] < 3 or sys.version_info[1] < 10:
    LOGGER.error(
        "3.11 버전 이상의 Python 이 있어야 합니다. 여러 기능이 Python3.11 버전을 따릅니다. 봇 종료."
    )
    quit(1)


from musicbot.config import Development as Config

TOKEN = Config.TOKEN
OWNERS = Config.OWNERS
DEBUG_SERVER = Config.DEBUG_SERVER
BOT_NAME = Config.BOT_NAME
BOT_TAG = Config.BOT_TAG
BOT_ID = Config.BOT_ID
COLOR_CODE = Config.COLOR_CODE
ABOUT_BOT = Config.ABOUT_BOT
HOST = Config.HOST
PSW = Config.PSW
REGION = Config.REGION
PORT = Config.PORT
LAVALINK_AUTO_UPDATE = Config.LAVALINK_AUTO_UPDATE
LAVALINK_PLUGINS = Config.LAVALINK_PLUGINS
SQL_HOST = Config.SQL_HOST
SQL_USER = Config.SQL_USER
SQL_PASSWORD = Config.SQL_PASSWORD
SQL_DB = Config.SQL_DB

KOREANBOT_TOKEN = Config.KOREANBOT_TOKEN
TOPGG_TOKEN = Config.TOPGG_TOKEN

BASE_DIR = Config.BASE_DIR
DB_NAME = Config.DB_NAME
DB_PATH = Config.DB_PATH

EXTENSIONS = []
for file in os.listdir("musicbot/cogs"):
    if file.endswith(".py"):
        EXTENSIONS.append(file.replace(".py", ""))

BOT_NAME_TAG_VER = "%s%s | %s" % (BOT_NAME, BOT_TAG, BOT_VER)

Database().create_table()