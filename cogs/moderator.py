import discord
from discord.ext import commands
from discord import Embed
from discord.ext.commands import context
import random
import datetime
from colored import fore, back, style

from common import glob, logging

class Moderate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='cogs')
    async def _cogsMod(self, ctx: commands.Context, loadType=None, cogsName=None):
        def convertLoadType(loadType):
            if loadType == "load" or loadType == "l" or loadType == "lo":
                return "loaded"
            elif loadType == "unload" or loadType == "u" or loadType == "un":
                return "unloaded"
            elif loadType == "reload" or loadType == "r" or loadType == "re":
                return "reloaded"
            else:
                return None
                
        if ctx.author.id != int(glob.BOT_DEVLOPER_ID):
            return await ctx.message.add_reaction('❌')
        else:
            await ctx.message.add_reaction('✔️')

        cogs = []
        for i in self.bot.extensions.keys():
            cogs.append(i)
            
        async with ctx.typing():
            if loadType == None and cogsName == None:
                embed = Embed(title=f"{glob.bot.user}'s Cogs List", description="load, unload, reload is support", colour=random.randint(0, 16777215), timestamp=datetime.datetime.now(glob.TIMEZONE))
                embed.set_footer(text=f"{glob.bot.user}")
                fields = []
                num = 0
                for i in cogs:
                    fields.append([f"Cogs #{num}", f"**{i.replace('cogs.', '')}**", True])
                    num += 1
                for name, value, inline in fields:
                    embed.add_field(name=name, value=value, inline=inline)
                return await ctx.send(embed=embed)
            else:
                if cogsName == None:
                    return await ctx.send("cogs name error", delete_after=5.0)
                msg = await ctx.send("Please wait...")
                if cogsName == "*" or cogsName == "all":
                    msgs = ""
                    LoadType = convertLoadType(loadType)
                    if LoadType != None:
                        if loadType == "load" or loadType == "l" or loadType == "lo":
                            for i in cogs:
                                self.bot.load_extension(i)
                                msgs += f"Cogs **{i}** is successfully {LoadType}.\n"
                                await msg.edit(content=msgs)
                        elif loadType == "unload" or loadType == "u" or loadType == "un":
                            for i in cogs:
                                self.bot.unload_extension(i)
                                msgs += f"Cogs **{i}** is successfully {LoadType}.\n"
                                await msg.edit(content=msgs)
                        elif loadType == "reload" or loadType == "r" or loadType == "re":
                            for i in cogs:
                                self.bot.reload_extension(i)
                                msgs += f"Cogs **{i}** is successfully {LoadType}.\n"
                                await msg.edit(content=msgs)
                        else:
                            return await msg.edit(content = "command error!")
                    msgs += f"{LoadType} done."
                    await msg.edit(content=msgs)
                else:
                    if not cogsName in "cogs.":
                        cogsName = f"cogs.{cogsName}"
                    try:
                        if loadType == "load" or loadType == "l" or loadType == "lo":
                            self.bot.load_extension(cogsName)
                        elif loadType == "unload" or loadType == "u" or loadType == "un":
                            self.bot.unload_extension(cogsName)
                        elif loadType == "reload" or loadType == "r" or loadType == "re":
                            self.bot.reload_extension(cogsName)
                        else:
                            return await msg.edit(content = "command error!")
                    except discord.ext.commands.errors.ExtensionNotLoaded:
                        return await msg.edit(content = "cogs not exist.")
                    LoadType = convertLoadType(loadType)
                    logging.ConsoleLog("normal", None, f"{fore.LIGHT_YELLOW}Cogs {fore.LIGHT_BLUE}{cogsName} {fore.LIGHT_YELLOW}is {LoadType}.")
                    return await msg.edit(content=f"Cogs **{cogsName}** is successfully {LoadType}.")
                    

def setup(bot: commands.Bot):
    bot.add_cog(Moderate(bot))