import async_timeout
import copy
import re
import typing
import asyncio
import discord
import wavelink
import math
from bs4 import BeautifulSoup
from discord.ext import commands, menus
from EZPaginator import Paginator
from colored import fore, back, style
import datetime

from zeee_bot.modules import converter
from zeee_bot.modules.language import get_language
from zeee_bot.common import glob, mysql, logging

url_re = re.compile('https?:\\/\\/(?:www\\.)?.+')

class NoChannelProvided(commands.CommandError):
    pass

class IncorrectChannelError(commands.CommandError):
    pass

class Track(wavelink.Track):
    __slots__ = ('requester', )

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.requester = kwargs.get('requester')

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

    async def do_next(self) -> None:
        if self.is_playing or self.waiting:
            return

        if self.repeat:
            await self.play(self.before_track)
        else:
            try:
                self.waiting = True
                with async_timeout.timeout(300):
                    if not self.is_playing:
                        track = await self.queue.get()
            except asyncio.TimeoutError:
                return await self.teardown()

            await self.play(track)
            self.waiting = False

        # Invoke our players controller...
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
            
            track = self.current
            embed = discord.Embed(
                title=get_language(self.dj.id, "Music_Play_Now_Playing"),
                color=converter.converthex("#CD68CF"),
                timestamp=datetime.datetime.now(glob.TIMEZONE)
            )
            embed.add_field(name=get_language(self.dj.id, "Music_Play_selected_embed_SongNameField_Name"), value=f"[{Music.TitleToShort(track.title)} - `{Music.MillisToHourMinuteSecond(track.duration)}`]({track.uri})", inline=False)
            embed.add_field(name=get_language(self.dj.id, "Music_Play_selected_embed_RequesterField_Name"), value=self.dj.mention, inline=False)

            await self.context.send(embed=embed)
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

        embed = discord.Embed(title=f'Music Controller | {channel.name}', colour=0xebb145)
        embed.description = f'Now Playing:\n**`{track.title}`**\n\n'
        embed.set_thumbnail(url=track.thumb)

        embed.add_field(name='Duration', value=str(datetime.timedelta(milliseconds=int(track.length))))
        embed.add_field(name='Queue Length', value=str(qsize))
        embed.add_field(name='Volume', value=f'**`{self.volume}%`**')
        embed.add_field(name='Requested By', value=track.requester.mention)
        embed.add_field(name='Video URL', value=f'[Click Here!]({track.uri})')

        return embed

    async def is_position_fresh(self) -> bool:
        """Method which checks whether the player controller should be remade or updated."""
        try:
            async for message in self.context.channel.history(limit=5):
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


class PaginatorSource(menus.ListPageSource):
    """Player queue paginator class."""

    def __init__(self, entries, *, per_page=8):
        super().__init__(entries, per_page=per_page)

    async def format_page(self, menu: menus.Menu, page):
        embed = discord.Embed(title='Coming Up...', colour=0x4f0321)
        embed.description = '\n'.join(f'`{index}. {title}`' for index, title in enumerate(page, 1))

        return embed

    def is_paginating(self):
        # We always want to embed even on 1 page of results...
        return True


class Music(commands.Cog, wavelink.WavelinkMixin):
    
    def __init__(self, bot):
        self.bot = bot

        if not hasattr(bot, 'wavelink'):
            self.bot.wavelink = wavelink.Client(bot=self.bot)
        self.bot.loop.create_task(self.start_nodes())

    async def start_nodes(self):
        await self.bot.wait_until_ready()

        if self.bot.wavelink.nodes:
            previous = self.bot.wavelink.nodes.copy()

            for node in previous.values():
                await node.destroy()
                
        nodes = {
            'MAIN': {
                'host': str(glob.LAVALINK_HOST),
                'port': int(glob.LAVALINK_PORT),
                'rest_uri': f"http://{glob.LAVALINK_HOST}:{glob.LAVALINK_PORT}",
                'password': "owowo",
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
        current_track = payload.player.current
        payload.player.before_track = current_track

    @wavelink.WavelinkMixin.listener(event='on_track_stuck')
    @wavelink.WavelinkMixin.listener(event='on_track_end')
    @wavelink.WavelinkMixin.listener(event='on_track_exception')
    async def on_player_stop(self, node: wavelink.Node, payload):
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
        """Cog wide error handler."""
        if isinstance(error, IncorrectChannelError):
            return

        if isinstance(error, NoChannelProvided):
            return await ctx.send('You must be in a voice channel or provide one to connect to.')

    async def cog_check(self, ctx: commands.Context):
        """Cog wide check, which disallows commands in DMs."""
        if not ctx.guild:
            await ctx.send('Music commands are not available in Private Messages.')
            return False

        return True

    async def cog_before_invoke(self, ctx: commands.Context):
        """Coroutine called before command invocation.
        We mainly just want to check whether the user is in the players controller channel.
        """
        player: Player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player, context=ctx)

        if player.context:
            if player.context.channel != ctx.channel:
                await ctx.send(f'{ctx.author.mention}, you must be in {player.context.channel.mention} for this session.')
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
                await ctx.send(f'{ctx.author.mention}, you must be in `{channel.name}` to use voice commands.')
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
                return "🔟"
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
            seconds = f"0{str(seconds)}"
        if int(hours) == 0:
            return f"{minutes}:{seconds}"
        return f"{int(hours)}:{minutes}:{seconds}"


    @commands.command(name="play", aliases=["틀어", "재생", "재생해", "p"])
    async def play(self, ctx, *, query: str, channel: discord.VoiceChannel=None):
        msg = await ctx.send(get_language(ctx.author.id, "Music_Play_Please_Wait"))

        player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)
        if not player.is_connected:
            await ctx.invoke(self.connect)

        query = query.strip('<>')
        if not url_re.match(query):
            query = f'ytsearch:{query}'
        tracks = await self.bot.wavelink.get_tracks(query)

        selectTrack = None
        await msg.delete()
        if not tracks:
            embed = discord.Embed(
                title=get_language(ctx.author.id, "Music_Play_Search_Failed"),
                color=converter.converthex("#FFB27D"),
                timestamp=datetime.datetime.now(glob.TIMEZONE)
            )
            return await ctx.send(embed=embed)

        if tracks and not url_re.match(query):
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
                    return await ctx.send(embed=embed)
                    
                if selectMsg.content.isdigit():
                    await msg.delete()
                    selectTrack = tracks[int(selectMsg.content)-1]
                    track = Track(selectTrack.id, selectTrack.info, requester=ctx.author)
                    await player.queue.put(track)
                    break
        else:
            selectTrack = tracks[0]
            track = Track(selectTrack.id, selectTrack.info, requester=ctx.author)
            await player.queue.put(track)

        embed = discord.Embed(
            title=get_language(ctx.author.id, "Music_Play_selected_embed_title"),
            color=converter.converthex("#60C5F1"),
            timestamp=datetime.datetime.now(glob.TIMEZONE)
        )
        embed.add_field(name=get_language(ctx.author.id, "Music_Play_selected_embed_SongNameField_Name"), value=f"[{self.TitleToShort(selectTrack.title)} - `{self.MillisToHourMinuteSecond(selectTrack.duration)}`]({selectTrack.uri})", inline=False)
        embed.add_field(name=get_language(ctx.author.id, "Music_Play_selected_embed_RequesterField_Name"), value=ctx.author.mention, inline=True)
        embed.add_field(name="재생까지 남은 곡", value=f"{'지금!' if player.queue.qsize()-1 == 0 else player.queue.qsize()-1 + ' 곡'}", inline=True)
        embed.add_field(name="상태", value=f"음량: `{player.volume}%` ♪ 필터: `{player.equalizer}` ♪ 반복: `{'켜짐' if player.repeat else '꺼짐'}`", inline=False)
        await ctx.send(embed=embed)

        if not player.is_playing:
            await player.do_next()


    @commands.command(name="repeat", aliases=["반복", "반복재생"])
    async def repeat(self, ctx, *, channel: discord.VoiceChannel=None):
        player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)
        if player.repeat:
            msg = "껐"
            player.repeat = False
        else:
            msg = "켰"
            player.repeat = True
        embed = discord.Embed(
            title=get_language(ctx.author.id, "Music_Repeat_Toggle_embed_title").format(repeatmsg=msg),
            color=converter.converthex("#60C5F1"),
            timestamp=datetime.datetime.now(glob.TIMEZONE)
        )
        await ctx.send(embed=embed)


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
        await ctx.guild.change_voice_state(channel=channel, self_deaf=True)
        return await ctx.send(embed=embed)


    @commands.command(name="leave", aliases=['나가', 'disconnect', '퇴장', 'skrk'])
    async def disconnect(self, ctx, *, channel: discord.VoiceChannel=None):
        player = self.bot.wavelink.get_player(ctx.guild.id)
        if not player.is_connected:
            return await ctx.send(get_language(ctx.author.id, "Music_Disconnect_Not_Connected").format(mention=ctx.author.mention))
        if not channel:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                return await ctx.send(get_language(ctx.author.id, "Music_Disconnect_You_need_to_join_first").format(mention=ctx.author.mention))

        await ctx.message.add_reaction('✅')
        try:
            await player.teardown()
        except:
            pass

        return await player.disconnect()


    @commands.command(aliases=['v', 'vol', "볼륨", "음량"])
    async def volume(self, ctx: commands.Context, *, vol: int):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        if not 0 < vol < 101:
            embed = discord.Embed(
                title=get_language(ctx.author.id, "Music_Volume_Change_Wrong_Value"),
                color=converter.converthex("#60C5F1"),
                timestamp=datetime.datetime.now(glob.TIMEZONE)
            )
            return await ctx.send(embed=embed)

        await player.set_volume(vol)
        embed = discord.Embed(
            title=get_language(ctx.author.id, "Music_Volume_Change_Wrong_Value"),
            color=converter.converthex("#60C5F1"),
            timestamp=datetime.datetime.now(glob.TIMEZONE)
        )
        await ctx.send(embed=embed)
        await ctx.send(f'{vol}% 설정완료')


    @commands.command(hidden=True)
    async def vol_up(self, ctx: commands.Context):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        vol = int(math.ceil((player.volume + 10) / 10)) * 10

        if vol > 100:
            vol = 100
            await ctx.send('Maximum volume reached', delete_after=7)

        await player.set_volume(vol)


    @commands.command(hidden=True)
    async def vol_down(self, ctx: commands.Context):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        vol = int(math.ceil((player.volume - 10) / 10)) * 10

        if vol < 0:
            vol = 0
            await ctx.send('Player is currently muted', delete_after=10)

        await player.set_volume(vol)


def setup(bot):
    bot.add_cog(Music(bot))