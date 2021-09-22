import os
import re
import math
import discord
from bs4 import BeautifulSoup
from discord.ext import commands
from EZPaginator import Paginator
from colored import fore, back, style

url_re = re.compile('https?:\\/\\/(?:www\\.)?.+')

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

def setup(bot):
    bot.add_cog (Music (bot))