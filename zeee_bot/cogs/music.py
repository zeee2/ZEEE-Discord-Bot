import json
import pathlib
import time
import async_timeout
import copy
import re
import typing
import asyncio
import discord
import wavelink
import math
import datetime

import sponsorblock as sb
from wavelink.player import TrackPlaylist
from PIL import Image, ImageDraw
from discord.ext import commands, menus
from colored import fore, back, style
from melonapi import scrapeMelon

from zeee_bot.modules import converter
from zeee_bot.modules.language import get_language
from zeee_bot.common import glob, logging

url_re = re.compile('https?:\\/\\/(?:www\\.)?.+')

class NoChannelProvided(commands.CommandError):
    pass

class IncorrectChannelError(commands.CommandError):
    pass

class Track(wavelink.Track):
    __slots__ = ('requester', 'sponsorskip')

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.requester = kwargs.get('requester')
        self.sponsorskip = kwargs.get('sponsorskip')

class Player(wavelink.Player):
    """Custom wavelink Player class."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.context: commands.Context = kwargs.get('context', None)
        if self.context:
            self.dj: discord.Member = self.context.author

        self.queue = asyncio.Queue()
        self.controller = None

        self.waiting = False
        self.updating = False
        self.repeat = False
        self.before_track = None
        self.now_track = None
        self.sponsor_skip = True

    async def set_default_volume(self):
        await self.set_volume(25)

    async def do_next(self, force=False) -> None:
        if self.is_playing and not force or self.waiting and not force:
            return
        if self.repeat:
            await self.play(self.now_track)
        else:
            try:
                self.waiting = True
                with async_timeout.timeout(300):
                    if not self.is_playing or force:
                        track = await self.queue.get()
            except asyncio.TimeoutError:
                return await self.teardown()

            await self.play(track)

            if isinstance(track.sponsorskip, list):
                temp_seconds = 0
                for temp in track.sponsorskip:
                    if int(temp.duration.seconds) > 0 and temp.start < 60:
                        temp_seconds += temp.duration.seconds
                await self.seek(int(temp_seconds*1000))

            self.waiting = False

        await self.invoke_controller()

    async def invoke_controller(self) -> None:
        """Method which updates or sends a new player controller."""
        if self.updating:
            return

        self.updating = True

        if not self.controller:
            self.controller = InteractiveController(embed=self.build_embed(), player=self)
            await self.controller.start(self.context)

        elif not await self.is_position_fresh():
            try:
                await self.controller.message.delete()
            except discord.HTTPException:
                pass

            self.controller.stop()
            self.controller = InteractiveController(embed=self.build_embed(), player=self)
            # embed = self.build_embed()
            # await self.context.send(embed=embed)
            await self.controller.start(self.context)

        else:
            embed = self.build_embed()
            await self.controller.message.edit(content=None, embed=embed)

        self.updating = False

    def build_embed(self) -> typing.Optional[discord.Embed]:
        """Method which builds our players controller embed."""
        track = self.current
        if not track:
            return

        channel = self.bot.get_channel(int(self.channel_id))
        qsize = self.queue.qsize()

        embed = discord.Embed(
            title=get_language(self.context.author.id, "Music_Player_Controller_Embed_Title").format(channel = channel.name),
            colour=0xebb145,
            timestamp=datetime.datetime.now(glob.TIMEZONE)
        )
        embed.description = f'?????????: **[{track.title}]({track.uri})**\n\n'
        embed.set_thumbnail(url=track.thumb)
        embed.set_footer(text=f"{glob.bot.user}")

        embed.add_field(name='?????????', value=track.requester.mention, inline=False)
        embed.add_field(name='??????', value=str(datetime.timedelta(milliseconds=int(track.length))), inline=True)
        embed.add_field(name='????????????', value=str(qsize) + "???", inline=True)
        embed.add_field(name='??????', value=f'**`{self.volume}%`**', inline=True)
        embed.add_field(name='???????????????', value=f'**`{self.equalizer}`**', inline=True)

        return embed

    async def is_position_fresh(self) -> bool:
        """Method which checks whether the player controller should be remade or updated."""
        try:
            async for message in self.context.channel.history(limit=3):
                if message.id == self.controller.message.id:
                    return True
        except (discord.HTTPException, AttributeError):
            return False

        return False

    async def teardown(self):
        """Clear internal states, remove player controller and disconnect."""
        try:
            await self.controller.message.delete()
        except discord.HTTPException:
            pass

        self.controller.stop()

        try:
            await self.destroy()
        except KeyError:
            pass

class InteractiveController(menus.Menu):
    """The Players interactive controller menu class."""

    def __init__(self, *, embed: discord.Embed, player: Player):
        super().__init__(timeout=None)

        self.embed = embed
        self.player = player

    def update_context(self, payload: discord.RawReactionActionEvent):
        """Update our context with the user who reacted."""
        ctx = copy.copy(self.ctx)
        ctx.author = payload.member

        return ctx

    def reaction_check(self, payload: discord.RawReactionActionEvent):
        if payload.event_type == 'REACTION_REMOVE':
            return False

        if not payload.member:
            return False
        if payload.member.bot:
            return False
        if payload.message_id != self.message.id:
            return False
        if payload.member not in self.bot.get_channel(int(self.player.channel_id)).members:
            return False

        return payload.emoji in self.buttons

    async def send_initial_message(self, ctx: commands.Context, channel: discord.TextChannel) -> discord.Message:
        return await channel.send(embed=self.embed)

    @menus.button(emoji='\u25B6')
    async def resume_command(self, payload: discord.RawReactionActionEvent):
        """Resume button."""
        ctx = self.update_context(payload)

        command = self.bot.get_command('resume')
        ctx.command = command

        await self.bot.invoke(ctx)

    @menus.button(emoji='\u23F8')
    async def pause_command(self, payload: discord.RawReactionActionEvent):
        """Pause button"""
        ctx = self.update_context(payload)

        command = self.bot.get_command('pause')
        ctx.command = command

        await self.bot.invoke(ctx)

    @menus.button(emoji='\u23F9')
    async def stop_command(self, payload: discord.RawReactionActionEvent):
        """Stop button."""
        ctx = self.update_context(payload)

        command = self.bot.get_command('stop')
        ctx.command = command

        await self.bot.invoke(ctx)

    @menus.button(emoji='\u23ED')
    async def skip_command(self, payload: discord.RawReactionActionEvent):
        """Skip button."""
        ctx = self.update_context(payload)

        command = self.bot.get_command('skip')
        ctx.command = command

        await self.bot.invoke(ctx)

    @menus.button(emoji='\U0001F500')
    async def shuffle_command(self, payload: discord.RawReactionActionEvent):
        """Shuffle button."""
        ctx = self.update_context(payload)

        command = self.bot.get_command('shuffle')
        ctx.command = command

        await self.bot.invoke(ctx)

    @menus.button(emoji='\u2795')
    async def volup_command(self, payload: discord.RawReactionActionEvent):
        """Volume up button"""
        ctx = self.update_context(payload)

        command = self.bot.get_command('vol_up')
        ctx.command = command

        await self.bot.invoke(ctx)

    @menus.button(emoji='\u2796')
    async def voldown_command(self, payload: discord.RawReactionActionEvent):
        """Volume down button."""
        ctx = self.update_context(payload)

        command = self.bot.get_command('vol_down')
        ctx.command = command

        await self.bot.invoke(ctx)

    @menus.button(emoji='\U0001F1F6')
    async def queue_command(self, payload: discord.RawReactionActionEvent):
        """Player queue button."""
        ctx = self.update_context(payload)

        command = self.bot.get_command('queue')
        ctx.command = command

        await self.bot.invoke(ctx)


class Music(commands.Cog, wavelink.WavelinkMixin):
    def __init__(self, bot):
        self.bot = bot

        if not hasattr(bot, 'wavelink'):
            self.bot.wavelink = wavelink.Client(bot=self.bot)
        self.bot.loop.create_task(self.start_nodes())

    async def start_nodes(self):
        await self.bot.wait_until_ready()

        # if self.bot.wavelink.nodes:
        #     previous = self.bot.wavelink.nodes.copy()

        #     for node in previous.values():
        #         await node.destroy()
                
        nodes = {
            'MAIN': {
                'host': str(glob.LAVALINK_HOST),
                'port': int(glob.LAVALINK_PORT),
                'rest_uri': f"http://{glob.LAVALINK_HOST}:{glob.LAVALINK_PORT}",
                'password': f'{str(glob.LAVALINK_PASS)}',
                'identifier': 'MAIN',
                'region': 'us_central'
                }
            }

        for n in nodes.values():
            node = await self.bot.wavelink.initiate_node(**n)
            
    @wavelink.WavelinkMixin.listener()
    async def on_node_ready(self, node: wavelink.Node):
        logging.ConsoleLog("index", "NODE", f"{node.identifier} Node Ready.")

    @wavelink.WavelinkMixin.listener(event='on_track_start')
    async def on_player_start(self, node:wavelink.Node, payload):
        payload.player.now_track = payload.player.current

    @wavelink.WavelinkMixin.listener(event='on_track_stuck')
    @wavelink.WavelinkMixin.listener(event='on_track_end')
    @wavelink.WavelinkMixin.listener(event='on_track_exception')
    async def on_player_stop(self, node: wavelink.Node, payload):
        payload.player.before_track = payload.player.current
        await payload.player.do_next()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return

        player: Player = self.bot.wavelink.get_player(member.guild.id, cls=Player)

        if not player.channel_id or not player.context:
            player.node.players.pop(member.guild.id)
            return

        channel = self.bot.get_channel(int(player.channel_id))

        if member == player.dj and after.channel is None:
            for m in channel.members:
                if m.bot:
                    continue
                else:
                    player.dj = m
                    return

        elif after.channel == channel and player.dj not in channel.members:
            player.dj = member
        

    async def cog_command_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, IncorrectChannelError):
            return

        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title=get_language(ctx.author.id, "Music_Error_Handler_BadArgument"),
                description=get_language(ctx.author.id, "Music_Error_Handler_BadArgument_description").format(prefix=glob.BOT_PREFIX),
                color=converter.converthex(glob.ERROR_COLOR),
                timestamp=datetime.datetime.now(glob.TIMEZONE)
            )
            embed.set_footer(text=f"{glob.bot.user}")
            return await ctx.send(embed=embed)

        if isinstance(error, NoChannelProvided):
            embed = discord.Embed(
                title=get_language(ctx.author.id, "Music_Error_Handler_No_Channel_Provided"),
                color=converter.converthex(glob.ERROR_COLOR),
                timestamp=datetime.datetime.now(glob.TIMEZONE)
            )
            embed.set_footer(text=f"{glob.bot.user}")
            return await ctx.send(embed=embed)

    async def cog_check(self, ctx: commands.Context):
        """Cog wide check, which disallows commands in DMs."""
        if not ctx.guild:
            embed = discord.Embed(
                title=get_language(ctx.author.id, "Music_General_NO"),
                description=get_language(ctx.author.id, "Music_Error_Handler_Not_Allowed_in_DM"),
                color=converter.converthex(glob.ERROR_COLOR),
                timestamp=datetime.datetime.now(glob.TIMEZONE)
            )
            embed.set_footer(text=f"{glob.bot.user}")
            await ctx.send(embed=embed)
            return False

        return True

    async def cog_before_invoke(self, ctx: commands.Context):
        """Coroutine called before command invocation.
        We mainly just want to check whether the user is in the players controller channel.
        """
        player: Player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player, context=ctx)
        if player.context:
            if player.context.channel != ctx.channel:
                raise IncorrectChannelError

        if ctx.command.name == 'connect' and not player.context:
            return

        if not player.channel_id:
            return

        channel = self.bot.get_channel(int(player.channel_id))
        if not channel:
            return

        if player.is_connected:
            if ctx.author not in channel.members:
                embed = discord.Embed(
                    title=get_language(ctx.author.id, "Music_Error_Handler_Join_Voice_Channel").format(channel=f"{channel.mention}"),
                    color=converter.converthex(glob.ERROR_COLOR),
                    timestamp=datetime.datetime.now(glob.TIMEZONE)
                )
                embed.set_footer(text=f"{glob.bot.user}")
                await ctx.send(embed=embed)
                raise IncorrectChannelError

    def NumToEmojis(self, num):
        numbers = [int(i) for i in str(num)]
        textToReturn = ""
        for i in range(len(numbers)):
            if numbers[i] == 0 and numbers[i] < 10:
                textToReturn += ":zero:"
            elif numbers[i] == 1 and numbers[i] < 10:
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
            elif numbers[i] == 10:
                return "????"
        return textToReturn

    def TitleToShort(self, title):
        if len(title) >= 40:
            return title[:40] + "..."
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
            seconds = f"0{str(seconds)}"
        if int(hours) == 0:
            return f"{minutes}:{seconds}"
        return f"{int(hours)}:{minutes}:{seconds}"

    def drawProgressBar(self, d, x, y, w, h, progress, bg="black", fg="red", hasspnsorskip=False):
        w *= progress
        d.ellipse((x+w, y, x+h+w, y+h),fill=fg, outline=None)
        d.ellipse((x, y, x+h, y+h),fill=fg, outline=None)
        if hasspnsorskip:
            d.ellipse((x+w, y, x+h+w, y+h),fill='red', outline=None)
            d.ellipse((x, y, x+h, y+h),fill='red', outline=None)

        d.rectangle((x+(h/2), y, x+w+(h/2), y+h),fill=fg, outline=None)

        return d

    async def get_sponser(self, sbc, track):
        try:
            index = 0
            sponserList = []
            for temp in sbc.get_skip_segments(track.uri):
                index += 1
                if temp.category == "intro" or "music_offtopic":
                    sponserList.append(temp)
        except:
            pass
        return sponserList

    @commands.command(name="play", aliases=["??????", "??????", "?????????", "p"])
    async def play(self, ctx, *, query: str, channel: discord.VoiceChannel=None):
        msg = await ctx.send(get_language(ctx.author.id, "Music_Play_Please_Wait"))

        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)
        sbc = sb.Client()
        if not player.is_connected:
            await ctx.invoke(self.connect)
            await player.set_default_volume()

        query = query.strip('<>')
        if not url_re.match(query):
            query = f'ytsearch:{query}'
        tracks = await self.bot.wavelink.get_tracks(query)

        selectTrack = None
        await msg.delete()
        PlayList = []
        if not tracks:
            embed = discord.Embed(
                title=get_language(ctx.author.id, "Music_Play_Search_Failed"),
                color=converter.converthex("#FFB27D"),
                timestamp=datetime.datetime.now(glob.TIMEZONE)
            )
            embed.set_footer(text=f"{glob.bot.user}")
            return await ctx.send(embed=embed)

        if not url_re.match(query):
            embed = discord.Embed(
                title=get_language(ctx.author.id, "Music_Play_Track_Select_embed_title"),
                color=converter.converthex("#77A9DB"),
                timestamp=datetime.datetime.now(glob.TIMEZONE)
            )
            embed.set_footer(text=f"{glob.bot.user}")
            embed_tracks = ""
            index = 0
            for track in tracks:
                if index >= 10:
                    break
                index += 1

                icon = self.NumToEmojis(index)
                embed_tracks += f"{icon} | `{str(datetime.timedelta(milliseconds=int(track.length)))}` {self.TitleToShort(track.title)}\n"
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
                    embed.set_footer(text=f"{glob.bot.user}")
                    return await ctx.send(embed=embed)

                if not selectMsg.content.isdigit() or (int(selectMsg.content)-1) < 0 or (int(selectMsg.content)-1) > 9:
                    await msg.delete()
                    embed = discord.Embed(
                        title=get_language(ctx.author.id, "Music_Play_wrong_select"),
                        color=converter.converthex(glob.ERROR_COLOR),
                        timestamp=datetime.datetime.now(glob.TIMEZONE)
                    )
                    embed.set_footer(text=f"{glob.bot.user}")
                    return await ctx.send(embed=embed)
                    
                if selectMsg.content.isdigit():
                    await msg.delete()
                    selectTrack = tracks[int(selectMsg.content)-1]
                    sponserList = await self.get_sponser(sbc, selectTrack)

                    track = Track(selectTrack.id, selectTrack.info, requester=ctx.author, sponsorskip=sponserList)
                    await player.queue.put(track)
                    break
        else:
            if isinstance(tracks, TrackPlaylist):
                for TempTrack in tracks.tracks:
                    sponserList = await self.get_sponser(sbc, selectTrack)

                    track = Track(TempTrack.id, TempTrack.info, requester=ctx.author, sponsorskip=sponserList)
                    await player.queue.put(track)
                    PlayList.append(track)
            else:
                selectTrack = tracks[0]
                sponserList = await self.get_sponser(sbc, selectTrack)

                track = Track(selectTrack.id, selectTrack.info, requester=ctx.author, sponsorskip=sponserList)
                await player.queue.put(track)

        embed = discord.Embed(
            title=get_language(ctx.author.id, "Music_Play_Add_Playlist"),
            color=converter.converthex("#60C5F1"),
            timestamp=datetime.datetime.now(glob.TIMEZONE)
        )
        embed.set_footer(text=f"{glob.bot.user}")
        if len(PlayList) > 0:
            tempEmbedVal = ""
            AddCount = 0
            for temp in PlayList:
                AddCount += 1
                if temp == PlayList[len(PlayList)-1]:
                    tempEmbedVal += f"{temp.title} - `{str(datetime.timedelta(milliseconds=int(temp.length)))}`"
                else:
                    if len(tempEmbedVal) > 700:
                        tempEmbedVal += get_language(ctx.author.id, "Music_Play_Over_Embed").format(song=len(PlayList) - AddCount)
                        break
                    tempEmbedVal += f"{temp.title} - `{str(datetime.timedelta(milliseconds=int(temp.length)))}`\n"
            embed.add_field(name=get_language(ctx.author.id, "Music_Play_selected_embed_SongNameField_Name"), value=tempEmbedVal, inline=False)
            embed.add_field(name=get_language(ctx.author.id, "Music_Play_selected_embed_RequesterField_Name"), value=ctx.author.mention, inline=True)
            leftsong = 0
            if player.is_playing:
                leftsong = player.queue.qsize()+1-len(PlayList)
            else:
                leftsong = player.queue.qsize()-len(PlayList)
            if not leftsong == 0:
                embed.add_field(name=get_language(ctx.author.id, "Music_Play_Left_song_count_embed_title"), value=get_language(ctx.author.id, "Music_Play_Left_song_count_embed_value").format(count=leftsong), inline=True)
        else:
            embed.add_field(name=get_language(ctx.author.id, "Music_Play_selected_embed_SongNameField_Name"), value=f"[{selectTrack.title} - `{str(datetime.timedelta(milliseconds=int(track.length)))}`]({selectTrack.uri})", inline=False)
            embed.add_field(name=get_language(ctx.author.id, "Music_Play_selected_embed_RequesterField_Name"), value=ctx.author.mention, inline=True)
            if not player.queue.qsize()-1 == 0:
                embed.add_field(name=get_language(ctx.author.id, "Music_Play_Left_song_count_embed_title"), value=get_language(ctx.author.id, "Music_Play_Left_song_count_embed_value").format(count=player.queue.qsize()-1), inline=True)
        embed.add_field(name=get_language(ctx.author.id, "Music_Play_Add_Queue_info_embed_title"), value=get_language(ctx.author.id, "Music_Play_Add_Queue_info_embed_value").format(volume=player.volume, equalizer=player.equalizer, repeat='??????' if player.repeat else '??????', eq=player.equalizer), inline=False)
        await ctx.send(embed=embed)

        if not player.is_playing:
            await player.do_next()

    
    @commands.command(name="melon", aliases=["??????", "????????????", "??????100", "??????????????????", "??????", "t"])
    async def melon(self, ctx, *, channel: discord.VoiceChannel=None):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)
        node = self.bot.wavelink
        sbc = sb.Client()

        if not player.is_connected:
            await ctx.invoke(self.connect)
            await player.set_default_volume()

        embed = discord.Embed(
            title=get_language(ctx.author.id, "Music_Play_Please_Wait"),
            description=get_language(ctx.author.id, "Music_Play_Get_Melon_Top100_Data"),
            color=converter.converthex("#60C5F1"),
            timestamp=datetime.datetime.now(glob.TIMEZONE)
        )
        embed.set_footer(text=f"{glob.bot.user}")
        msg = await ctx.send(embed=embed)

        Top100 = []
        MelonData = json.loads(str(scrapeMelon.getList("LIVE").decode()))
        for melon_temp in MelonData:
            melon_temp = MelonData[f"{melon_temp}"]
            Top100.append(f"{melon_temp['artists']} {melon_temp['name']}")
        PlayList = []
        
        embed = discord.Embed(
            title=get_language(ctx.author.id, "Music_Play_Please_Wait"),
            description=get_language(ctx.author.id, "Music_Play_Append_Melon_Top100_Data"),
            color=converter.converthex("#60C5F1"),
            timestamp=datetime.datetime.now(glob.TIMEZONE)
        )
        embed.set_footer(text=f"{glob.bot.user}")

        await msg.edit(embed=embed)

        query = f'https://www.youtube.com/watch?v=kTJczUoc26U&list=PL2HEDIx6Li8jGsqCiXUq9fzCqpH99qqHV'
        tracks = await node.get_tracks(query)

        if isinstance(tracks, TrackPlaylist):
            for TempTrack in tracks.tracks:
                sponserList = await self.get_sponser(sbc, TempTrack)
                asyncio.sleep(0.75)

                track = Track(TempTrack.id, TempTrack.info, requester=ctx.author, sponsorskip=sponserList)
                await player.queue.put(track)
                
                PlayList.append(track)

                if not player.is_playing:
                    await ctx.send(get_language(ctx.author.id, "Music_Play_While_Append_Melon_Top100_Data_Playing_Top1"))
                    await player.do_next()
        else:
            selectTrack = tracks[0]
            sponserList = await self.get_sponser(sbc, selectTrack)
            asyncio.sleep(0.75)

            track = Track(selectTrack.id, selectTrack.info, requester=ctx.author, sponsorskip=sponserList)
            await player.queue.put(track)

            PlayList.append(track)

        embed = discord.Embed(
            title=get_language(ctx.author.id, "Music_Play_Add_Playlist"),
            color=converter.converthex("#60C5F1"),
            timestamp=datetime.datetime.now(glob.TIMEZONE)
        )
        embed.set_footer(text=f"{glob.bot.user}")
        tempEmbedVal = ""
        AddCount = 0
        for temp in PlayList:
            AddCount += 1
            if temp == PlayList[len(PlayList)-1]:
                tempEmbedVal += f"{temp.title} - `{str(datetime.timedelta(milliseconds=int(temp.length)))}`"
            else:
                if len(tempEmbedVal) > 700:
                    tempEmbedVal += get_language(ctx.author.id, "Music_Play_Over_Embed").format(song=len(PlayList) - AddCount)
                    break
                tempEmbedVal += f"{temp.title} - `{str(datetime.timedelta(milliseconds=int(temp.length)))}`\n"
        embed.add_field(name=get_language(ctx.author.id, "Music_Play_selected_embed_SongNameField_Name"), value=tempEmbedVal, inline=False)
        embed.add_field(name=get_language(ctx.author.id, "Music_Play_selected_embed_RequesterField_Name"), value=ctx.author.mention, inline=True)
        leftsong = 0
        if player.is_playing:
            leftsong = player.queue.qsize()+1-len(PlayList)
        else:
            leftsong = player.queue.qsize()-len(PlayList)
        if not leftsong == 0:
            embed.add_field(name=get_language(ctx.author.id, "Music_Play_Left_song_count_embed_title"), value=get_language(ctx.author.id, "Music_Play_Left_song_count_embed_value").format(count=leftsong), inline=True)

        await msg.delete()
        await ctx.send(embed=embed)

        if not player.is_playing:
            await player.do_next()


    @commands.command(name="before", aliases=["?????????", "??????", "?????????", "??????", "???", "????????????"])
    async def before_song(self, ctx, *, channel: discord.VoiceChannel=None):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)
        sbc = sb.Client()

        if not player.is_connected:
            embed = discord.Embed(
                title=get_language(ctx.author.id, "Music_General_Not_Connected"),
                color=converter.converthex(glob.ERROR_COLOR),
                timestamp=datetime.datetime.now(glob.TIMEZONE)
            )
            embed.set_footer(text=f"{glob.bot.user}")
            return await ctx.send(embed=embed)
        
        temp = player.before_track
                                                        
        sponserList = await self.get_sponser(sbc, temp)
        track = Track(temp.id, temp.info, requester=ctx.author, sponsorskip=sponserList)
        await player.queue.put(track)

        embed = discord.Embed(
            title=get_language(ctx.author.id, "Music_Play_Add_Playlist"),
            color=converter.converthex("#60C5F1"),
            timestamp=datetime.datetime.now(glob.TIMEZONE)
        )
        embed.set_footer(text=f"{glob.bot.user}")
        embed.add_field(name=get_language(ctx.author.id, "Music_Play_selected_embed_SongNameField_Name"), value=f"[{temp.title} - `{str(datetime.timedelta(milliseconds=int(track.length)))}`]({temp.uri})", inline=False)
        embed.add_field(name=get_language(ctx.author.id, "Music_Play_selected_embed_RequesterField_Name"), value=ctx.author.mention, inline=True)
        if not player.queue.qsize()-1 == 0:
            embed.add_field(name=get_language(ctx.author.id, "Music_Play_Left_song_count_embed_title"), value=get_language(ctx.author.id, "Music_Play_Left_song_count_embed_value").format(count=player.queue.qsize()-1), inline=True)

        embed.add_field(name=get_language(ctx.author.id, "Music_Play_Add_Queue_info_embed_title"), value=get_language(ctx.author.id, "Music_Play_Add_Queue_info_embed_value").format(volume=player.volume, equalizer=player.equalizer, repeat='??????' if player.repeat else '??????', eq=player.equalizer), inline=False)
        await ctx.send(embed=embed)
        

    @commands.command(name="equalizer", aliases=["???????????????", "eq", "dlznjffkdlwj", "??????"])
    async def equalizer(self, ctx, *, eq: str="None"):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)
        
        if not player.is_connected:
            embed = discord.Embed(
                title=get_language(ctx.author.id, "Music_General_Not_Connected"),
                color=converter.converthex(glob.ERROR_COLOR),
                timestamp=datetime.datetime.now(glob.TIMEZONE)
            )
            embed.set_footer(text=f"{glob.bot.user}")
            return await ctx.send(embed=embed)

        eq_list = {'flat': wavelink.Equalizer.flat(),
                'boost': wavelink.Equalizer.boost(),
                'metal': wavelink.Equalizer.metal(),
                'piano': wavelink.Equalizer.piano()}

        EQ = eq_list.get(eq.lower(), None)
        if EQ == None:
            embed = discord.Embed(
                title=get_language(ctx.author.id, "Music_Equalizer_List_embed_title"),
                description=get_language(ctx.author.id, "Music_Equalizer_List_embed_description").format(prefix=glob.BOT_PREFIX),
                color=converter.converthex("#60C5F1"),
                timestamp=datetime.datetime.now(glob.TIMEZONE)
            )
            embed.set_footer(text=f"{glob.bot.user}")

            for eq in eq_list.keys():
                embed.add_field(name=eq, value=get_language(ctx.author.id, f"Music_Equalizer_{eq}_Description"))

            return await ctx.send(embed=embed)
        
        await player.set_eq(EQ)
        embed = discord.Embed(
            title=get_language(ctx.author.id, "Music_Equalizer_Change_Successful").format(eq=eq),
            color=converter.converthex("#3EDF6D"),
            timestamp=datetime.datetime.now(glob.TIMEZONE)
        )
        embed.set_footer(text=f"{glob.bot.user}")

        await ctx.send(embed=embed)
        

    @commands.command(name="seek", aliases=["??????", "dnlcl", "?????????", "???????????????"])
    async def seek(self, ctx, *, position: str, channel: discord.VoiceChannel=None):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            embed = discord.Embed(
                title=get_language(ctx.author.id, "Music_General_Not_Connected"),
                color=converter.converthex(glob.ERROR_COLOR),
                timestamp=datetime.datetime.now(glob.TIMEZONE)
            )
            embed.set_footer(text=f"{glob.bot.user}")
            return await ctx.send(embed=embed)

        if not ":" in position or position == "" or position == None:
            embed = discord.Embed(
                title=get_language(ctx.author.id, "Music_Seek_format_Error_embed_title"),
                description=get_language(ctx.author.id, "Music_Seek_format_Error_embed_value"),
                color=converter.converthex(glob.ERROR_COLOR),
                timestamp=datetime.datetime.now(glob.TIMEZONE)
            )
            embed.set_footer(text=f"{glob.bot.user}")
            return await ctx.send(embed=embed)

        positionSplit = position.split(":")
        track_time = 0
        if len(positionSplit) == 2:
            track_time += (int(positionSplit[0]) * 60000) + (int(positionSplit[1]) * 1000)
        elif len(positionSplit) == 3:
            track_time += (int(positionSplit[0]) * 60 * 60 * 1000) + (int(positionSplit[1]) * 60000) + (int(positionSplit[2]) * 1000)    
        await player.seek(track_time)

        embed = discord.Embed(
            title=get_language(ctx.author.id, "Music_Seek_Successful").format(position=position),
            color=converter.converthex("#007AAE"),
            timestamp=datetime.datetime.now(glob.TIMEZONE)
        )
        embed.set_footer(text=f"{glob.bot.user}")
        embed.add_field(name=get_language(ctx.author.id, "Music_General_Requester"), value=ctx.author.mention)
        await ctx.send(embed=embed)
    

    @commands.command(name="repeat", aliases=["??????", "????????????"])
    async def repeat(self, ctx, *, channel: discord.VoiceChannel=None):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)
        if player.repeat:
            msg = "???"
            player.repeat = False
        else:
            msg = "???"
            player.repeat = True
        embed = discord.Embed(
            title=get_language(ctx.author.id, "Music_Repeat_Toggle_embed_title").format(repeatmsg=msg),
            color=converter.converthex("#60C5F1"),
            timestamp=datetime.datetime.now(glob.TIMEZONE)
        )
        embed.set_footer(text=f"{glob.bot.user}")
        await ctx.send(embed=embed)


    @commands.command(name="join", aliases=['?????????', '??????', 'whdls', '??????', 'emfdjdhk'])
    async def connect(self, ctx, *, channel: discord.VoiceChannel=None):
        if not channel:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                raise discord.DiscordException('No channel to join. Please either specify a valid channel or join one.')

        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)
        embed = discord.Embed(
            title=get_language(ctx.author.id, "Music_Connect_Embed_title").format(channel=channel.name),
            color=converter.converthex("#6BD089"),
            timestamp=datetime.datetime.now(glob.TIMEZONE)
        )
        embed.set_footer(text=f"{glob.bot.user}")
        await player.connect(channel.id)
        await ctx.guild.change_voice_state(channel=channel, self_deaf=True)
        return await ctx.send(embed=embed)


    @commands.command(name="leave", aliases=['??????', 'disconnect', '??????', 'skrk'])
    async def disconnect(self, ctx, *, channel: discord.VoiceChannel=None):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)
        if not player.is_connected:
            embed = discord.Embed(
                title=get_language(ctx.author.id, "Music_General_Not_Connected"),
                color=converter.converthex("#FF7A6B"),
                timestamp=datetime.datetime.now(glob.TIMEZONE)
            )
            embed.set_footer(text=f"{glob.bot.user}")
            return await ctx.send(embed=embed)
            
        if not channel:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                return await ctx.send(get_language(ctx.author.id, "Music_Disconnect_You_need_to_join_first").format(mention=ctx.author.mention))

        await ctx.message.add_reaction('???')
        try:
            await player.teardown()
        except:
            pass

        return await player.disconnect()


    @commands.command(name="skip", aliases=["??????", "??????", "????????????", "????????????", "?????????", "?????????", "??????", "?????????"])
    async def skip(self, ctx, *, channel: discord.VoiceChannel=None):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            embed = discord.Embed(
                title=get_language(ctx.author.id, "Music_General_Not_Connected"),
                color=converter.converthex("#FF7A6B"),
                timestamp=datetime.datetime.now(glob.TIMEZONE)
            )
            embed.set_footer(text=f"{glob.bot.user}")
            return await ctx.send(embed=embed)
        
        await player.do_next(force=True)
        embed = discord.Embed(
            title=get_language(ctx.author.id, "Music_Skip_OK"),
            color=converter.converthex("#6BD089"),
            timestamp=datetime.datetime.now(glob.TIMEZONE)
        )
        embed.set_footer(text=f"{glob.bot.user}")
        embed.add_field(name=get_language(ctx.author.id, "Music_General_Requester"), value=ctx.author.mention)
        await ctx.send(embed=embed)

    
    @commands.command(name="nowplay", aliases=["np", "??????", "??????", "????????????", "???????????????", "??????"])
    async def nowplay(self, ctx: commands.Context):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)
        msg = await ctx.send(get_language(ctx.author.id, "Music_General_Please_wait"))

        if not player.is_connected or player.position == 0:
            embed = discord.Embed(
                title=get_language(ctx.author.id, "Music_General_Not_Connected"),
                color=converter.converthex("#FF7A6B"),
                timestamp=datetime.datetime.now(glob.TIMEZONE)
            )
            embed.set_footer(text=f"{glob.bot.user}")
            return await ctx.send(embed=embed)

        current = player.current
        length = current.length

        base_img = Image.open(f"{pathlib.Path(__file__).parent.parent}/images/base/now_base.png").convert("RGBA")
        draw = ImageDraw.Draw(base_img)
        percent = (player.position / length * 100) / 100
        draw = self.drawProgressBar(draw, 15, 11, 572.5, 28.5, percent, bg=(35, 39, 48), fg=(96, 197, 241))
        fileName = f"{ctx.guild.id}{current.ytid}{int(time.time())}.png"

        base_img = base_img.resize((567, 45), resample=Image.ANTIALIAS)
        base_img = base_img.resize((567, 45), resample=Image.ANTIALIAS)
        base_img = base_img.resize((567, 45), resample=Image.ANTIALIAS)
        base_img = base_img.resize((567, 45), resample=Image.ANTIALIAS)
        base_img = base_img.resize((567, 45), resample=Image.ANTIALIAS)
        base_img.save(f'./zeee_bot/images/{fileName}')

        await msg.delete()
        embed = discord.Embed(
            title=get_language(ctx.author.id, "Music_NP_Embed_Title"),
            color=converter.converthex("#FF7A6B"),
            timestamp=datetime.datetime.now(glob.TIMEZONE)
        )
        embed.set_thumbnail(url=current.thumb)
        embed.add_field(name=get_language(ctx.author.id, "Music_NP_Embed_Field_SongName"), value=f"[{current.title}]({current.uri})", inline=False)
        embed.add_field(name=get_language(ctx.author.id, "Music_NP_Embed_Field_Nowlength"), value=f"{self.MillisToHourMinuteSecond(player.position)}", inline=True)
        embed.add_field(name=get_language(ctx.author.id, "Music_NP_Embed_Field_TotalLength"), value=f"{self.MillisToHourMinuteSecond(current.length)}", inline=True)
        embed.add_field(name=get_language(ctx.author.id, "Music_General_Requester"), value=f"{player.dj.mention}", inline=False)
        embed.set_footer(text=f"{glob.bot.user}")
        embed.set_image(url=f"https://rinaring.zeee.dev/{fileName}")
        await ctx.send(embed=embed)


    @commands.command(name="pause", aliases=["??????", "????????????", "??????", "??????", "??????!"])
    async def pause(self, ctx: commands.Context):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)
        
        if not player.is_connected or not player.is_playing:
            embed = discord.Embed(
                title=get_language(ctx.author.id, "Music_General_Not_Connected"),
                color=converter.converthex("#FF7A6B"),
                timestamp=datetime.datetime.now(glob.TIMEZONE)
            )
            embed.set_footer(text=f"{glob.bot.user}")
            return await ctx.send(embed=embed)
        
        await player.set_pause(pause=True)
        embed = discord.Embed(
            title=get_language(ctx.author.id, "Music_Pause_Successful"),
            color=converter.converthex(glob.ERROR_COLOR),
            timestamp=datetime.datetime.now(glob.TIMEZONE)
        )
        embed.set_footer(text=f"{glob.bot.user}")
        await ctx.send(embed=embed)


    @commands.command(name="resume", aliases=["????????????", "??????", "????????????", "?????????", "ektltlwkr"])
    async def resume(self, ctx: commands.Context):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)
        
        if not player.is_connected or not player.is_playing:
            embed = discord.Embed(
                title=get_language(ctx.author.id, "Music_General_Not_Connected"),
                color=converter.converthex("#FF7A6B"),
                timestamp=datetime.datetime.now(glob.TIMEZONE)
            )
            embed.set_footer(text=f"{glob.bot.user}")
            return await ctx.send(embed=embed)
        
        await player.set_pause(pause=False)
        embed = discord.Embed(
            title=get_language(ctx.author.id, "Music_Resume_Successful"),
            color=converter.converthex(glob.ERROR_COLOR),
            timestamp=datetime.datetime.now(glob.TIMEZONE)
        )
        embed.set_footer(text=f"{glob.bot.user}")
        await ctx.send(embed=embed)


    @commands.command(aliases=['v', 'vol', "??????", "??????"])
    async def volume(self, ctx: commands.Context, *, vol: int):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            embed = discord.Embed(
                title=get_language(ctx.author.id, "Music_General_Not_Connected"),
                color=converter.converthex("#FF7A6B"),
                timestamp=datetime.datetime.now(glob.TIMEZONE)
            )
            embed.set_footer(text=f"{glob.bot.user}")
            return await ctx.send(embed=embed)

        if not 1<= vol <= 150:
            embed = discord.Embed(
                title=get_language(ctx.author.id, "Music_Volume_Change_Wrong_Value"),
                color=converter.converthex(glob.ERROR_COLOR),
                timestamp=datetime.datetime.now(glob.TIMEZONE)
            )
            embed.set_footer(text=f"{glob.bot.user}")
            return await ctx.send(embed=embed)

        await player.set_volume(vol)
        embed = discord.Embed(
            title=get_language(ctx.author.id, "Music_Volume_Change_Successful").format(vol=player.volume),
            color=converter.converthex("#60C5F1"),
            timestamp=datetime.datetime.now(glob.TIMEZONE)
        )
        embed.set_footer(text=f"{glob.bot.user}")
        embed.add_field(name=get_language(ctx.author.id, "Music_General_Requester"), value=ctx.author.mention)
        await player.invoke_controller()
        await ctx.send(embed=embed)


    @commands.command(hidden=True)
    async def vol_up(self, ctx: commands.Context):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            embed = discord.Embed(
                title=get_language(ctx.author.id, "Music_General_Not_Connected"),
                color=converter.converthex("#FF7A6B"),
                timestamp=datetime.datetime.now(glob.TIMEZONE)
            )
            embed.set_footer(text=f"{glob.bot.user}")
            return await ctx.send(embed=embed)

        vol = int(math.ceil((player.volume + 10) / 10)) * 10

        if vol > 150:
            vol = 150
            embed = discord.Embed(
                title=get_language(ctx.author.id, "Music_Volume_Change_Max").format(vol=player.volume),
                color=converter.converthex("#60C5F1"),
                timestamp=datetime.datetime.now(glob.TIMEZONE)
            )
            embed.set_footer(text=f"{glob.bot.user}")
            embed.add_field(name=get_language(ctx.author.id, "Music_General_Requester"), value=ctx.author.mention)
            await ctx.send(embed=embed)

        await player.invoke_controller()
        await player.set_volume(vol)


    @commands.command(hidden=True)
    async def vol_down(self, ctx: commands.Context):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            embed = discord.Embed(
                title=get_language(ctx.author.id, "Music_General_Not_Connected"),
                color=converter.converthex("#FF7A6B"),
                timestamp=datetime.datetime.now(glob.TIMEZONE)
            )
            embed.set_footer(text=f"{glob.bot.user}")
            return await ctx.send(embed=embed)

        vol = int(math.ceil((player.volume - 10) / 10)) * 10

        if vol < 0:
            vol = 0
            embed = discord.Embed(
                title=get_language(ctx.author.id, "Music_Volume_Change_Min").format(vol=player.volume),
                color=converter.converthex("#60C5F1"),
                timestamp=datetime.datetime.now(glob.TIMEZONE)
            )
            embed.set_footer(text=f"{glob.bot.user}")
            embed.add_field(name=get_language(ctx.author.id, "Music_General_Requester"), value=ctx.author.mention)
            await ctx.send(embed=embed)

        await player.invoke_controller()
        await player.set_volume(vol)


def setup(bot):
    bot.add_cog(Music(bot))