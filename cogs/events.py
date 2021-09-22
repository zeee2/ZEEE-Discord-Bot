import discord
from discord.ext import commands
from discord import Embed
from discord.ext.commands import context
import random
from colored import fore, back, style
import datetime

from common import glob, logging
from modules import language


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        logging.ConsoleLog("normal", "bot", f"{fore.PLUM_1}{glob.bot.user} {fore.LIGHT_MAGENTA}is ready")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.content == glob.BOT_PREFIX:
            ctx = await self.bot.get_context(message)
            embed = Embed(
                title=language.get_language(message.author.id, "prefix_hi_title"),
                description=language.get_language(message.author.id, "prefix_hi_description").format(BOT_PREFIX = glob.BOT_PREFIX),
                colour=random.randint(0, 16777215),
                timestamp=datetime.datetime.now(glob.TIMEZONE)
            )
            embed.set_footer(text=f"{glob.bot.user}")
            await ctx.send(embed = embed)


def setup(bot):
    bot.add_cog(Events(bot))