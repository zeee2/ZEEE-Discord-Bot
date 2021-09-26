from discord import Activity, ActivityType
from discord.ext import commands
from discord import Embed
from discord.ext import tasks
from discord.ext.commands import context
from discord.ext.tasks import loop
import random
from colored import fore, back, style
import datetime
from itertools import cycle
import os
import time

from zeee_bot.common import glob, logging
from zeee_bot.modules import language



class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        self.status_list = None


    @commands.Cog.listener()
    async def on_ready(self):
        logging.ConsoleLog("normal", "bot", f"{fore.PLUM_1}{glob.bot.user} {fore.LIGHT_MAGENTA}is ready")
        self.status_list = cycle([f'{len(self.bot.guilds)}서버에 서식중 🍥 {glob.BOT_PREFIX}초대', f'{len(self.bot.users)}유저들과 노는중 🍥 {glob.BOT_PREFIX}초대'])
        self.bot_loop.start()
        logging.ConsoleLog("ok", "LOOP-System", f"Bot Status Loop Start.")
        self.music_npImage_cron.start()
        logging.ConsoleLog("ok", "LOOP-System", f"Bot Music-NP images cron Loop Start.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.content == glob.BOT_PREFIX or glob.bot.user.mentioned_in(message):
            ctx = await self.bot.get_context(message)
            embed = Embed(
                title=language.get_language(message.author.id, "prefix_hi_title"),
                description=language.get_language(message.author.id, "prefix_hi_description").format(BOT_PREFIX = glob.BOT_PREFIX),
                colour=random.randint(0, 16777215),
                timestamp=datetime.datetime.now(glob.TIMEZONE)
            )
            embed.set_footer(text=f"{glob.bot.user}")
            await ctx.send(embed = embed)
        # if glob.bot.user.mentioned_in(message):

    
    @tasks.loop(seconds=10.0)
    async def bot_loop(self):
        status = f"{next(self.status_list)}"
        activity = Activity(name=status, type=ActivityType.listening)
        await self.bot.change_presence(activity=activity)
    
    @tasks.loop(minutes=30.0)
    async def music_npImage_cron(self):
        deleted = []
        for temp in os.listdir(f"{glob.BASEROOT}/zeee_bot/images"):
            if not temp == "now_base.png":
                file_root = f"{glob.BASEROOT}/zeee_bot/images/{temp}"
                file_generate_time = int(os.path.getmtime(file_root))
                now = int(time.time()) + 10
                if (file_generate_time - now) > 0:
                    os.remove(file_root)
                    deleted.append(temp)
        
        if len(deleted) > 0:
            t = ""
            for i in deleted:
                t += i+" "
            logging.ConsoleLog("ok", "Music-NP-CRONJOB", f"{t} 삭제됨.")



def setup(bot):
    bot.add_cog(Events(bot))