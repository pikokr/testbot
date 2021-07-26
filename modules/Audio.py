import asyncio

import async_timeout
import discord
import wavelink
from discord.ext import commands
from wavelink import Track

from client import Client


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

    async def do_next(self) -> None:
        if self.is_playing or self.waiting:
            return

        try:
            self.waiting = True
            with async_timeout.timeout(300):
                track = await self.queue.get()
        except asyncio.TimeoutError:
            # No music has been played for 5 minutes, cleanup and disconnect...
            return await self.teardown()

        await self.play(track)
        self.waiting = False

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


class Audio(commands.Cog, wavelink.WavelinkMixin):
    def __init__(self, bot: Client):
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

        nodes = {'MAIN': {'host': 'localhost',
                          'port': 2333,
                          'rest_uri': 'http://localhost:2333',
                          'password': 'youshallnotpass',
                          'identifier': 'MAIN',
                          'region': 'MAIN'
                          }}

        for n in nodes.values():
            await self.bot.wavelink.initiate_node(**n)

    @wavelink.WavelinkMixin.listener()
    async def on_node_ready(self, node: wavelink.Node):
        print(f'Node {node.identifier} is ready!')

    @wavelink.WavelinkMixin.listener('on_track_stuck')
    @wavelink.WavelinkMixin.listener('on_track_end')
    @wavelink.WavelinkMixin.listener('on_track_exception')
    async def on_player_stop(self, node: wavelink.Node, payload):
        await payload.player.do_next()

    @commands.command()
    async def connect(self, ctx: commands.Context):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player)

        if player.is_connected:
            return

        channel = getattr(ctx.author.voice, 'channel')
        if channel is None:
            return await ctx.reply('우으...음성채널에 들어가주새오!')

        await player.connect(channel.id)

    @commands.command()
    async def play(self, ctx: commands.Context, *, query: str):
        tracks = await self.bot.wavelink.get_tracks(f'ytsearch:{query}')

        if not tracks:
            return await ctx.send('으에... 검색 결과가 없어오!')

        player: Player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)

        if not player.is_connected:
            await ctx.invoke(self.connect)

        if isinstance(tracks, wavelink.TrackPlaylist):
            for track in tracks.tracks:
                track = Track(track.id, track.info)
                await player.queue.put(track)

            await ctx.send(f'와아아! 영상 {len(tracks.tracks)}개를 대기열에 추가했어오!')

        await ctx.send(f'와아아! 영상 `{str(tracks[0])}` 을 대기열에 추가했어오!')
        await player.queue.put(tracks[0])

        if not player.is_playing:
            await player.do_next()

    @commands.command()
    async def skip(self, ctx: commands.Context):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        if not player:
            return ctx.reply()
        await player.stop()
        await ctx.send('스킵했어오! >ㅅ<')
