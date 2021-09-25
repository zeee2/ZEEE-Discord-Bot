import os
import requests
import json
import pathlib
import discord
from discord.ext import commands
from dislash import InteractionClient
from colored import fore, back, style
import sys
import platform
from urllib import request
from pytz import timezone
import time
import multiprocessing

from zeee_bot.common import mysql, glob, logging
from zeee_bot.modules import lavalinkstart, cogsLoadder


class RinaRing(commands.Bot):
    def __init__(self):
        super().__init__ (
            command_prefix=glob.BOT_PREFIX,
            status=discord.Status.online,
            activity=discord.Game(f"조금만 기다려주세요! 현재 작동 준비중 이랍니다."),
            intents=discord.Intents.all(),
            help_command=None,
            afk=True
        )

        # self.SETUP_LAVALINK()
        # time.sleep(10)

    def SETUP_LAVALINK(self):
        logging.ConsoleLog("ok", 'LAVALINK', "Checking lavalink.jar...")
        a = requests.get("https://api.github.com/repos/Cog-Creators/Lavalink-Jars/releases")
        b = json.loads(a.text)
        if not os.path.isfile(f"{str(pathlib.Path(__file__).parent.parent)}/Lavalink.jar"):
            logging.ConsoleLog("war", 'LAVALINK', "Download start lavalink.jar...")
            request.urlretrieve(f"https://github.com/Cog-Creators/Lavalink-Jars/releases/download/{b[0]['tag_name']}/Lavalink.jar", f"Lavalink.jar")
            if platform.system() == "Linux":
                os.system("chmod -R 777 ./Lavalink.jar")
        process = multiprocessing.Process(target=lavalinkstart.child_process)
        process.start()

        logging.ConsoleLog("ok", 'LAVALINK', "Setup Done.")

bot = RinaRing()
slash = InteractionClient(bot)

cogsLoadder.loadAll_cogs(bot)

glob.slash = slash
glob.bot = bot
glob.client = bot
glob.inter_client = slash


glob.bot.run(glob.BOT_TOKEN)