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

from zeee_bot.common import glob, logging
from zeee_bot.modules import language



class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        self.status_list = cycle([f'{len(bot.guilds)}서버에 서식중 🍥 {glob.BOT_PREFIX}초대', f'{len(bot.users)}유저들과 노는중 🍥 {glob.BOT_PREFIX}초대'])


    @commands.Cog.listener()
    async def on_ready(self):
        logging.ConsoleLog("normal", "bot", f"{fore.PLUM_1}{glob.bot.user} {fore.LIGHT_MAGENTA}is ready")
        self.bot_loop.start()

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


def setup(bot):
    bot.add_cog(Events(bot))