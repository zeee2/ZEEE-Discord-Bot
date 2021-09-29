import os

from discord import FFmpegPCMAudio
from discord.ext import commands
from discord.utils import get as disget
from youtube_dl import YoutubeDL
from yt_dlp import YoutubeDL as YTDLP
from requests import get
from dislash import InteractionClient, ActionRow, Button, ButtonStyle, SelectMenu, SelectOption
from colored import fore, back, style
from PIL import Image, ImageFont, ImageDraw, ImageEnhance
from discord.ext import commands
import discord

from zeee_bot.common import glob

class TestMusic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def search(self, query):
        # info = None
        with YTDLP({'format': 'bestaudio', 'noplaylist':'True'}) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            return info
        # print(glob.BASEROOT)
        # os.system(f"{glob.BASEROOT}/zeee_bot/bin/yt-dlp1 https://www.youtube.com/watch?v=ALj5MKjy2BU -N 8 --audio-multistreams -f best/bestaudio -x --audio-quality 0 --ffmpeg-location {glob.BASEROOT}/zeee_bot/bin/ffmpeg --sponskrub-cut --sponskrub-force --sponskrub-location {glob.BASEROOT}/zeee_bot/bin/sponskrub1 -k")

    @commands.command(name="테스트")
    async def test(self, ctx: commands.Context, *, query: str, channel: discord.VoiceChannel=None):
        # FFMPEG_OPTS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
        chan = ctx.message.author.voice.channel
        voice = disget(self.bot.voice_clients, guild=ctx.guild)

        if voice and voice.is_connected():
            await voice.move_to(channel)
        else:
            voice = await chan.connect()

        src = self.search(query)
        # voice = get(self.bot.voice_clients, channel=channel)
        # voice = disget(self.bot.voice_clients, guild=ctx.guild)

        # await self.join(ctx, channel)
        await ctx.send(f"Now playing `BTS (방탄소년단) 'Permission to Dance' Official MV.wav`.")

        voice.play(FFmpegPCMAudio(f"{glob.BASEROOT}/[MV] BTS(방탄소년단) _ FIRE (불타오르네) [ALj5MKjy2BU].m4a"), after=lambda e: print('done', e))\
        # song = FFmpegPCMAudio(src["formats"][0]["url"], **FFMPEG_OPTS)
        # await ctx.voice_state.songs.put(song)
        # voice.is_playing()


def setup(bot: commands.Bot):
    bot.add_cog(TestMusic(bot))