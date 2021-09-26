from os import name
import pathlib
from discord.ext import commands
import discord
from dislash import InteractionClient, ActionRow, Button, ButtonStyle, SelectMenu, SelectOption
from colored import fore, back, style
from PIL import Image, ImageFont, ImageDraw, ImageEnhance

from zeee_bot.common import glob

class Test(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="test")
    async def ___test(self, ctx):
        row = ActionRow(
            Button(
                style=ButtonStyle.green,
                label="sexy bread",
                custom_id="bread_btn"
            )
        )
        msg = await ctx.send("마 눌러바라 게이야", components=[row])
        on_click = msg.create_click_listener(timeout=5)

        @on_click.matching_id("bread_btn")
        async def on_bread_button(inter):
            await inter.reply("헤으응 부끄러웟", delete_after=2.5)
        
        @on_click.timeout
        async def on_timeout():
            await msg.delete()
            await ctx.send("응애 타임아웃!")

    def drawProgressBar(self, d, x, y, w, h, progress, bg="black", fg="red"):
        # draw background
        d.ellipse((x+w, y, x+h+w, y+h), fill=bg, outline=None)
        d.ellipse((x, y, x+h, y+h), fill=bg, outline=None)
        d.rectangle((x+(h/2), y, x+w+(h/2), y+h), fill=bg, outline=None)

        # draw progress bar
        w *= progress
        d.ellipse((x+w, y, x+h+w, y+h),fill=fg, outline=None)
        d.ellipse((x, y, x+h, y+h),fill=fg, outline=None)
        d.rectangle((x+(h/2), y, x+w+(h/2), y+h),fill=fg, outline=None)

        return d

    @commands.command(name='ㅅ')
    async def testtest(self, ctx):
        a = 'get base img.'
        msg = await ctx.send(a)

        base_img = Image.open(f"{pathlib.Path(__file__).parent.parent}/images/now_base.png").convert("RGBA")
        draw = ImageDraw.Draw(base_img)
        color = (96, 197, 241)
        draw = self.drawProgressBar(draw, 15, 11, 572.5, 29, 0.5, bg=color, fg=color)

        # ImageDraw.floodfill(base_img, xy=(14,24), value=color, thresh=40)
        a += "\nwriting image."
        await msg.edit(content=a)
        
        base_img.save('test2.png')

        a += "\nDone."
        await msg.delete()
        await ctx.send(file=discord.File("test2.png"))

    @commands.command(name="test2")
    async def __test2(self, ctx):
        msg = await ctx.send(
            "마 한번 골라바라 게이야",
            components=[
                SelectMenu(
                    custom_id = "bread_sexy",
                    placeholder="골라바라 게이야 낄낄",
                    max_values=2,
                    options=[
                        SelectOption("빵", "빵"),
                        SelectOption("빵빵", "빵빵"),
                        SelectOption("빵빵빵", "빵빵빵")
                    ]
                )
            ]
        )
        inter = await msg.wait_for_dropdown()
        labels = [option.value for option in inter.select_menu.selected_options]
        await msg.edit(content="골라부럇구만!", components=[])
        await inter.reply(f"{''.join(labels)}")


def setup(bot: commands.Bot):
    bot.add_cog(Test(bot))