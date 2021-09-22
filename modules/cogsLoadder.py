import datetime
from colored import fore, back, style
import os

from common import logging

def loadAll_cogs(bot):
    logging.ConsoleLog("normal", "cogs", f"{fore.LIGHT_YELLOW}Cogs {fore.LIGHT_BLUE}jishaku {fore.LIGHT_YELLOW}loding...")
    bot.load_extension(f'jishaku')
    logging.ConsoleLog("normal", "cogs", f"{fore.LIGHT_YELLOW}Cogs {fore.LIGHT_BLUE}jishaku {fore.LIGHT_YELLOW}is successfully loaded")
    for cogs in os.listdir('./cogs'):
        if cogs.endswith('.py'):
            logging.ConsoleLog("normal", "cogs", f"{fore.LIGHT_YELLOW}Cogs {fore.LIGHT_BLUE}{cogs[:-3]} {fore.LIGHT_YELLOW}loding...")
            bot.load_extension(f'cogs.{cogs[:-3]}')
            logging.ConsoleLog("normal", "cogs", f"{fore.LIGHT_YELLOW}Cogs {fore.LIGHT_BLUE}{cogs[:-3]} {fore.LIGHT_YELLOW}is successfully loaded")