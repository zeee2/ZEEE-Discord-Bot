import pathlib
import discord
from discord.ext import commands
from dislash import InteractionClient
from colored import fore, back, style
import sys
import os
from pytz import timezone
import json
from urllib import request
import requests
import time
import multiprocessing

from common import mysql, glob, logging
from modules import config, cogsLoadder, lavalinkstart


def asciiArt():
    print(fore.GREEN_YELLOW, "    .-'''-.                     .-'''-.     ")
    print(fore.GREEN_YELLOW, "   '   _    \                  '   _    \   ")
    print(fore.GREEN_YELLOW, " /   /` '.   \               /   /` '.   \  ")
    print(fore.GREEN_YELLOW, ".   |     \  '       _     _.   |     \  '  ")
    print(fore.GREEN_YELLOW, "|   '      |  '/\    \\\   //|   '      |  ' ")
    print(fore.GREEN_YELLOW, "\    \     / / `\\\  //\\\ // \    \     / /  ")
    print(fore.GREEN_YELLOW, " `.   ` ..' /    \`//  \\'/   `.   ` ..' /   ")
    print(fore.GREEN_YELLOW, "    '-...-'`      \|   |/       '-...-'`    ")
    print(fore.GREEN_YELLOW, "                   '                     ")
    print(f"{style.RESET}===============================\n")


def CONFIG_LOADER():
    # conf = config.settings
    # glob.BOT_TOKEN = conf['token']
    # glob.BOT_PREFIX = conf['prefix']
    # glob.BOT_ID = int(conf['bot_id'])
    # glob.BOT_DEVLOPER_ID = conf['devloper_id']
    # glob.SQL_HOST = conf['SQL_Host']
    # glob.SQL_USER = conf['SQL_Username']
    # glob.SQL_PASS = conf['SQL_Password']
    # glob.SQL_DB = conf['SQL_DB']
    # glob.TIMEZONE = timezone(conf['timezone'])
    # glob.LAVALINK_HOST = conf['Lavalink_host']
    # glob.LAVALINK_PORT = int(conf['Lavalink_port'])
    # glob.LAVALINK_PASS = conf['Lavalink_password']

    # if any(not i for i in [glob.BOT_TOKEN, glob.BOT_PREFIX, glob.BOT_DEVLOPER_ID, glob.TIMEZONE, glob.SQL_HOST, glob.SQL_USER, glob.SQL_PASS, glob.SQL_DB, glob.LAVALINK_HOST, glob.LAVALINK_PORT, glob.LAVALINK_PASS]):
    #     logging.ConsoleLog("danger", 'config', "Config load Failed.")
    #     sys.exit()
    conf = config.config(str(glob.BASEROOT) + "/config.ini")
    if conf.default:
        logging.ConsoleLog("war", "config", "config.ini is not found. A default one has been generated.")
        sys.exit()
    if not conf.checkConfig():
        logging.ConsoleLog("war", "config", "Invaild config.ini. Please configure it properly")
        logging.ConsoleLog("war", "config", "Delete config.ini to generate a default one.")
        sys.exit()

    glob.BOT_TOKEN = conf.config['bot']['token']
    glob.BOT_PREFIX = conf.config['bot']['prefix']
    glob.BOT_DEVLOPER_ID = conf.config['bot']['devloper_id']
    glob.SQL_HOST = conf.config['db']['host']
    glob.SQL_USER = conf.config['db']['username']
    glob.SQL_PASS = conf.config['db']['password']
    glob.SQL_DB = conf.config['db']['database']
    glob.TIMEZONE = timezone(conf.config['general']['timezone'])    
    glob.LAVALINK_HOST = conf.config['lavalink']['host'] 
    glob.LAVALINK_PORT = int(conf.config['lavalink']['port'])    
    glob.LAVALINK_PASS = conf.config['lavalink']['password']

    if any(not i for i in [glob.BOT_TOKEN, glob.BOT_PREFIX, glob.BOT_DEVLOPER_ID, glob.TIMEZONE, glob.SQL_HOST, glob.SQL_USER, glob.SQL_PASS, glob.SQL_DB, glob.LAVALINK_HOST, glob.LAVALINK_PORT, glob.LAVALINK_PASS]):
        logging.ConsoleLog("danger", 'config', "Config load Failed.")
        sys.exit()


def BOT_RUN():
    game = discord.Game(f"조금만 기다려주세요! 현재 작동 준비중 이랍니다.")
    bot = commands.Bot(
        command_prefix=glob.BOT_PREFIX,
        status=discord.Status.online,
        activity=game,
        intents=discord.Intents.all(),
        help_command=None,
        afk=True
    )
    slash = InteractionClient(bot)

    glob.slash = slash
    glob.bot = bot
    glob.client = bot
    glob.inter_client = slash
    
    cogsLoadder.loadAll_cogs(bot)

    glob.bot.run(glob.BOT_TOKEN)


def WRITE_LAVALINK_SETTING():
    logging.ConsoleLog("ok", 'LAVALINK', "Setup start...")
    f = open("application.yml", 'w')
    f.write(f"""server:
    port: {glob.LAVALINK_PORT}
    address: {glob.LAVALINK_HOST}
    lavalink:
    server:
        password: youshallnotpass
        sources:
        youtube: true
        bandcamp: true
        soundcloud: true
        twitch: true
        vimeo: true
        mixer: true
        http: true
        local: false
        bufferDurationMs: 400
        youtubePlaylistLoadLimit: 6
        playerUpdateInterval: 5
        youtubeSearchEnabled: true
        soundcloudSearchEnabled: true
        gc-warnings: true
    metrics:
    prometheus:
        enabled: false
        endpoint: /metrics
    sentry:
    dsn: ""
    environment: ""
    logging:
    file:
        max-history: 30
        max-size: 1GB
    path: ./logs/
    level:
        root: INFO
        lavalink: INFO""")
    f.close()

def SETUP_LAVALINK():
    logging.ConsoleLog("ok", 'LAVALINK', "Start Lavalink...")
    WRITE_LAVALINK_SETTING()
    time.sleep(5)
    a = requests.get("https://api.github.com/repos/Cog-Creators/Lavalink-Jars/releases")
    b = json.loads(a.text)
    if not os.path.isfile(f"{str(glob.BASEROOT)}/Lavalink-{b[0]['tag_name']}.jar"):
        request.urlretrieve(f"https://github.com/Cog-Creators/Lavalink-Jars/releases/download/{b[0]['tag_name']}/Lavalink.jar", f"Lavalink-{b[0]['tag_name']}.jar")
    # os.system(f"java -jar Lavalink-{b[0]['tag_name']}.jar")   
    logging.ConsoleLog("ok", 'LAVALINK', "Setup Done.")

    process = multiprocessing.Process(target=lavalinkstart.child_process)
    # process.start()
    time.sleep(5)


def Load():
    asciiArt()
    glob.BASEROOT = pathlib.Path(__file__).parent.parent
    CONFIG_LOADER()
    # SETUP_LAVALINK()
    mysql.DB_CONNECT()
    BOT_RUN()