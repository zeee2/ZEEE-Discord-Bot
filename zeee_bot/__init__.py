import os
import requests
import json
import pathlib
import discord
from discord.ext import commands
from dislash import InteractionClient
from colored import fore, back, style
import sys
from urllib import request
from pytz import timezone
import time
import multiprocessing
import logging as syslog

from zeee_bot.common import mysql, glob, logging
from zeee_bot.modules import config

loggingFormat = fore.BLACK + back.GREEN_YELLOW + " [ %(levelname)s ] " + style.RESET + "|" + fore.GREY_37 + back.WHITE + " %(asctime)s " + style.RESET + "|| %(message)s"

syslog.basicConfig(
    format=loggingFormat,
    level=syslog.INFO)
LOGGER = syslog.getLogger(__name__)


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


def WRITE_LAVALINK_SETTING():
    logging.ConsoleLog("ok", 'LAVALINK', "Setup start...")
    f = open("application.yml", 'w')
    f.write(f"""server:
    port: {glob.LAVALINK_PORT}
    address: {glob.LAVALINK_HOST}
    lavalink:
    server:
        password: "{glob.LAVALINK_PASS}"
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

asciiArt()
glob.BASEROOT = pathlib.Path(__file__).parent.parent
CONFIG_LOADER()
WRITE_LAVALINK_SETTING()
mysql.DB_CONNECT()