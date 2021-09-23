from modules.language import get_language
import os
import re
import math
import discord
import wavelink
from bs4 import BeautifulSoup
from discord.ext import commands
from EZPaginator import Paginator
from colored import fore, back, style
import datetime

from modules import converter
from common import glob

url_re = re.compile('https?:\\/\\/(?:www\\.)?.+')

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        if not hasattr(bot, 'wavelink'):
            self.bot.wavelink = wavelink.Client(bot=self.bot)
        self.bot.loop.create_task(self.start_nodes())

    async def start_nodes(self):
        await self.bot.wait_until_ready()
        await self.bot.wavelink.initiate_node(host=str(glob.LAVALINK_HOST),
                                              port=int(glob.LAVALINK_PORT),
                                              rest_uri=f"http://{glob.LAVALINK_HOST}:{glob.LAVALINK_PORT}",
                                              password=str(glob.LAVALINK_PASS),
                                              identifier='TEST',
                                              region='us_central')
                            
    def cog_unload(self):
        self.bot.wavelink.destroy_node()

    def NumToEmojis(self, num):
        numbers = [int(i) for i in str(num)]
        textToReturn = ""
        for i in range(len(numbers)):
            if numbers[i] == 0:
                textToReturn += ":zero:"
            elif numbers[i] == 1:
                textToReturn += ":one:"
            elif numbers[i] == 2:
                textToReturn += ":two:"
            elif numbers[i] == 3:
                textToReturn += ":three:"
            elif numbers[i] == 4:
                textToReturn += ":four:"
            elif numbers[i] == 5:
                textToReturn += ":five:"
            elif numbers[i] == 6:
                textToReturn += ":six:"
            elif numbers[i] == 7:
                textToReturn += ":seven:"
            elif numbers[i] == 8:
                textToReturn += ":eight:"
            elif numbers[i] == 9:
                textToReturn += ":nine:"
        return textToReturn

    def TitleToShort(self, title):
        if len(title) >= 31:
            return title[:30]
        else:
            return title

    def MillisToHourMinuteSecond(self, milli):
        millis = int(milli)
        seconds=(millis/1000)%60
        seconds = int(seconds)
        minutes=(millis/(1000*60))%60
        minutes = int(minutes)
        hours=(millis/(1000*60*60))%24
        if len(str(minutes)) == 1:
            minutes = f"0{str(minutes)}"
        if len(str(seconds)) == 1:
            minutes = f"0{str(seconds)}"
        if int(hours) == 0:
            return f"{minutes}:{seconds}"
        return f"{int(hours)}:{minutes}:{seconds}"

    @commands.command(name="play", aliases=["틀어", "재생", "재생해", "p"])
    async def play(self, ctx, *, query: str, channel: discord.VoiceChannel=None):
        msg = await ctx.send(get_language(ctx.author.id, "Music_Play_Please_Wait"))

        player = self.bot.wavelink.get_player(ctx.guild.id)
        if not player.is_connected:
            await self.connect(ctx)
        await msg.delete()
        
        tracks = await self.bot.wavelink.get_tracks(f'ytsearch:{query}')

        if not tracks:
            embed = discord.Embed(
                title=get_language(ctx.author.id, "Music_Play_Search_Failed"),
                color=converter.converthex("#FFB27D"),
                timestamp=datetime.datetime.now(glob.TIMEZONE)
            )
            return await ctx.send(embed=embed)

        if not url_re.match(query):
            embed = discord.Embed(
                title=get_language(ctx.author.id, "Music_Play_Track_Select_embed_title"),
                color=converter.converthex("#77A9DB"),
                timestamp=datetime.datetime.now(glob.TIMEZONE)
            )
            embed_tracks = ""
            index = 0
            for track in tracks:
                if index >= 10:
                    break
                index += 1
                icon = self.NumToEmojis(index)
                embed_tracks += f"{icon} | `{self.MillisToHourMinuteSecond(track.duration)}` {self.TitleToShort(track.title)}\n"
            embed.add_field(name=get_language(ctx.author.id, "Music_Play_Track_Select_embed_field_name"), value=embed_tracks, inline=False)
            msg = await ctx.send(embed=embed)
            def check(msg):
                return msg.author == ctx.author
            while True:
                try:
                    selectMsg = await self.bot.wait_for("message", timeout=60, check=check)
                except:
                    await msg.delete()
                    embed = discord.Embed(
                        title=get_language(ctx.author.id, "Music_Play_select_Timeout"),
                        color=converter.converthex("#D64F50"),
                        timestamp=datetime.datetime.now(glob.TIMEZONE)
                    )
                    return await ctx.send(embed=embed)

                if not selectMsg.content.isdigit() or (int(selectMsg.content)-1) < 0 or (int(selectMsg.content)-1) > 9:
                    await msg.delete()
                    embed = discord.Embed(
                        title=get_language(ctx.author.id, "Music_Play_wrong_select"),
                        color=converter.converthex("#DB75A5"),
                        timestamp=datetime.datetime.now(glob.TIMEZONE)
                    )
                    await ctx.send(embed=embed)
                    
                if selectMsg.content.isdigit():
                    await msg.delete()
                    TrackSelected = tracks[int(selectMsg.content)-1]
                    embed = discord.Embed(
                        title=get_language(ctx.author.id, "Music_Play_selected_embed_title"),
                        color=converter.converthex("#60C5F1"),
                        timestamp=datetime.datetime.now(glob.TIMEZONE)
                    )
                    embed.add_field(name=get_language(ctx.author.id, "Music_Play_selected_embed_SongNameField_Name"), value=f"[{self.TitleToShort(TrackSelected.title)} - `{self.MillisToHourMinuteSecond(TrackSelected.duration)}`]({TrackSelected.uri})", inline=False)
                    embed.add_field(name=get_language(ctx.author.id, "Music_Play_selected_embed_RequesterField_Name"), value=ctx.author.mention, inline=False)
                    await player.play(TrackSelected)
                    return await ctx.send(embed=embed)
        else:
            await player.play(tracks[0])

    @commands.command(name="join", aliases=['들어와', '조인', 'whdls', '입장', 'emfdjdhk'])
    async def connect(self, ctx, *, channel: discord.VoiceChannel=None):
        if not channel:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                raise discord.DiscordException('No channel to join. Please either specify a valid channel or join one.')

        player = self.bot.wavelink.get_player(ctx.guild.id)
        embed = discord.Embed(
            title=get_language(ctx.author.id, "Music_Connect_Embed_title").format(channel=channel.name),
            color=converter.converthex("#6BD089"),
            timestamp=datetime.datetime.now(glob.TIMEZONE)
        )
        embed.set_footer(text=f"{glob.bot.user}")
        await player.connect(channel.id)
        return await ctx.send(embed=embed)


    @commands.command(name="leave", aliases=['나가', 'disconnect', '퇴장', 'skrk'])
    async def disconnect(self, ctx, *, channel: discord.VoiceChannel=None):
        player = self.bot.wavelink.get_player(ctx.guild.id)
        if not player.is_connected:
            return await ctx.send(get_language(ctx.author.id, "Music_Disconnect_Not_Connected").format(mention=ctx.autor.mention))
        if not channel:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                return await ctx.send(get_language(ctx.author.id, "Music_Disconnect_You_need_to_join_first").format(mention=ctx.autor.mention))

        await ctx.message.add_reaction('✅')

        return await player.disconnect()


def setup(bot):
    bot.add_cog(Music(bot))