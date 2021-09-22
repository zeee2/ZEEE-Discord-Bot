import pathlib
import discord
from discord.ext import commands
from dislash import InteractionClient
from dislash.interactions.application_command import Type
from colored import fore, back, style
import sys
from pytz import timezone

from common import mysql, glob, logging
from modules import config, cogsLoadder


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
    
    if any(not i for i in [glob.BOT_TOKEN, glob.BOT_PREFIX, glob.BOT_DEVLOPER_ID, glob.TIMEZONE, glob.SQL_HOST, glob.SQL_USER, glob.SQL_PASS, glob.SQL_DB]):
        logging.ConsoleLog("danger", 'config', "Config load Failed.")
        sys.exit()


def BOT_RUN():
    game = discord.Game(f"For ZEEE#4444")
    bot = commands.Bot(
        command_prefix=glob.BOT_PREFIX,
        status=discord.Status.online,
        activity=game,
        intents=discord.Intents.all(),
        help_command=None
    )
    slash = InteractionClient(bot)

    glob.slash = slash
    glob.bot = bot
    glob.client = bot
    glob.inter_client = slash
    
    cogsLoadder.loadAll_cogs(bot)

    glob.bot.run(glob.BOT_TOKEN)


def Load():
    asciiArt()
    glob.BASEROOT = pathlib.Path(__file__).parent.parent
    # config.config_load()
    CONFIG_LOADER()
    mysql.DB_CONNECT()
    BOT_RUN()