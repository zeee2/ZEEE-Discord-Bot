import pathlib
import os

from colored import fore, back, style

from zeee_bot.common import logging

def loadAll_cogs(bot):
    logging.ConsoleLog("normal", "cogs", f"{fore.LIGHT_YELLOW}Cogs {fore.LIGHT_BLUE}jishaku {fore.LIGHT_YELLOW}loding...")
    bot.load_extension(f'jishaku')
    logging.ConsoleLog("normal", "cogs", f"{fore.LIGHT_YELLOW}Cogs {fore.LIGHT_BLUE}jishaku {fore.LIGHT_YELLOW}is successfully loaded")
    for cogs in os.listdir(f'{pathlib.Path(__file__).parent.parent}/cogs'):
        if cogs.endswith('.py'):
            logging.ConsoleLog("normal", "cogs", f"{fore.LIGHT_YELLOW}Cogs {fore.LIGHT_BLUE}{cogs[:-3]} {fore.LIGHT_YELLOW}loding...")
            bot.load_extension(f'zeee_bot.cogs.{cogs[:-3]}')
            logging.ConsoleLog("normal", "cogs", f"{fore.LIGHT_YELLOW}Cogs {fore.LIGHT_BLUE}{cogs[:-3]} {fore.LIGHT_YELLOW}is successfully loaded")