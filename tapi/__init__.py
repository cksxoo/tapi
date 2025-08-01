import os
import sys
import logging


# Bot version
BOT_VER = "v0.7.2"

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


from tapi.config import Development as Config

TOKEN = Config.TOKEN
OWNERS = Config.OWNERS
DEBUG_SERVER = Config.DEBUG_SERVER
APPLICATION_NAME = Config.APPLICATION_NAME
APP_TAG = Config.APP_TAG
CLIENT_ID = Config.CLIENT_ID
THEME_COLOR = Config.THEME_COLOR
IDLE_COLOR = Config.IDLE_COLOR
APP_DESCRIPTION = Config.APP_DESCRIPTION
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
for file in os.listdir("tapi/modules"):
    if file.endswith(".py"):
        EXTENSIONS.append(file.replace(".py", ""))

APP_NAME_TAG_VER = "%s%s | %s" % (APPLICATION_NAME, APP_TAG, BOT_VER)

# Initialize database after all imports are complete
from tapi.utils.database import Database
Database().create_table()