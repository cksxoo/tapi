if not __name__.endswith("sample_config"):
    import sys

    print(
        "This sample_config is read-only. Do not modify this file directly. "
        "Create your own config file by extending this template. Ignoring this warning may cause issues.\nBot shutting down.",
        file=sys.stderr,
    )
    quit(1)


class Config(object):
    TOKEN = ""  # Bot token
    OWNERS = [123456789]  # Administrator IDs
    DEBUG_SERVER = []  # Debug server IDs
    APPLICATION_NAME = ""  # Application name
    APP_TAG = "#"  # Bot tag
    CLIENT_ID = 123456789  # Client ID
    APP_DESCRIPTION = ""  # Application description
    THEME_COLOR = 0xC68E6E  # Theme color code

    # Music
    HOST = "0.0.0.0"
    PSW = ""  # Lavalink password
    REGION = "eu"  # Server region
    PORT = 2333
    LAVALINK_AUTO_UPDATE = False
    LAVALINK_PLUGINS = {
        "com.github.topi314.lavasrc:lavasrc-plugin": "https://api.github.com/repos/topi314/LavaSrc/releases",
        "dev.lavalink.youtube:youtube-plugin": "https://api.github.com/repos/lavalink-devs/youtube-source/releases",
    }

    # Bot listing sites
    KOREANBOT_TOKEN = None
    TOPGG_TOKEN = None

    # SQL
    SQL_HOST = "localhost"
    SQL_USER = "root"
    SQL_PASSWORD = ""
    SQL_DB = "tapi_bot"


class Production(Config):
    LOGGER = False


class Development(Config):
    LOGGER = True
