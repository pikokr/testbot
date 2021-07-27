import asyncio
import itertools
import math
import typing

import discord
from discord.ext import commands

import discodo

from client import Client

NEWLINE = "\n"


def getProgress(value, Total):
    position_front = round(value / Total * 10)
    position_back = 10 - position_front

    return "▬" * position_front + "🔘" + "▬" * position_back


def formatDuration(seconds):
    seconds = int(seconds)
    minute, second = divmod(seconds, 60)
    hour, minute = divmod(minute, 60)

    return (f"{hour:02}:" if hour else "") + f"{minute:02}:{second:02}"


class SubtitleCallback:
    def __init__(self, channel: discord.TextChannel):
        self.loop = asyncio.get_event_loop()

        self._message: typing.Optional[discord.Message] = None
        self.channel: discord.TextChannel = channel

    async def callback(self, subtitle: str) -> None:
        if not self._message or self.channel.last_message.id != self._message.id:
            if self._message:
                self.loop.create_task(self._message.delete())

            self._message = await self.channel.send(
                f'{subtitle.get("previous", "")}\n> {subtitle["current"]}\n{subtitle.get("next") or ""}'
            )
        else:
            await self._message.edit(
                content=f'{subtitle.get("previous", "")}\n> {subtitle["current"].replace(NEWLINE, f"{NEWLINE}> ")}\n{subtitle.get("next") or ""}'
            )


class Audio(commands.Cog):
    def __init__(self, Bot: Client):
        self.Bot = Bot
        self.Audio = Bot.Audio

        self.Audio.dispatcher.on("SOURCE_START", self.on_source_start)

    async def on_source_start(self, voice_client, data):
        context = await voice_client.getContext()
        channel = await self.Bot.fetch_channel(context.get("text_channel"))

        await channel.send(f"Now playing {data['source'].title}...")

    @commands.is_owner()
    @commands.command()
    async def connectnodes(self, ctx):
        """Connect to the discodo nodes."""

        def getText():
            return f"""
> **Discodo Node Connection**
>
{NEWLINE.join(map(lambda x: '> ' + ('🛠️  `' if not x.is_connected else '✅  `') + x.region + '`', ctx.bot.Audio.Nodes))}
"""

        message = await ctx.send(getText())

        for Node in ctx.bot.Audio.Nodes:
            try:
                await Node.connect()
            finally:
                await message.edit(content=getText())

    @commands.command()
    async def join(self, ctx):
        """Connect to the voice channel."""

        if not ctx.author.voice:
            return await ctx.reply("Join the voice channel first.")

        try:
            VC = await self.Audio.connect(ctx.author.voice.channel)
        except discodo.NodeNotConnected:
            return await ctx.send("There is no available node.")
        except asyncio.TimeoutError:
            return await ctx.send("The connection is not established in 10 seconds.")

        await VC.setContext({"text_channel": ctx.channel.id})

        await ctx.reply(f"Successfully connected to {ctx.author.voice.channel}")

    @commands.command()
    async def play(self, ctx, *, query: str):
        """Play a source with the query."""

        if not ctx.voice_client:
            await ctx.invoke(self.join)

        Sources = await ctx.voice_client.loadSource(query)
        if not Sources:
            return await ctx.reply("There is no search result.")

        if isinstance(Sources, list):
            await ctx.reply(f"Added {len(Sources)} sources to the queue.")
        else:
            await ctx.reply(f"Added {Sources.title} sources to the queue.")

        await asyncio.gather(
            *list(
                map(
                    lambda x: x.setContext({"requester": ctx.author.id}),
                    Sources if isinstance(Sources, list) else [Sources],
                )
            )
        )

    @commands.command()
    async def pause(self, ctx):
        """Pause the player."""

        if not ctx.voice_client:
            return await ctx.reply("I'm not playing anything.")

        await ctx.voice_client.pause()

        await ctx.reply("Paused playing.")

    @commands.command()
    async def resume(self, ctx):
        """Resume the player."""

        if not ctx.voice_client:
            return await ctx.reply("I'm not playing anything.")

        await ctx.voice_client.resume()

        await ctx.reply("Resumed playing.")

    @commands.command()
    async def skip(self, ctx):
        """Skip the currently playing."""

        if not ctx.voice_client:
            return await ctx.reply("I'm not playing anything.")

        Current = await ctx.voice_client.getCurrent()

        if ctx.author.id == Current["context"].get("requester"):
            await ctx.reply("The source requester has skipped the source.")

            return await ctx.voice_client.skip()

        if "skip_votes" not in Current["context"]:
            Current["context"]["skip_votes"] = []

        if ctx.author.id in Current["context"]["skip_votes"]:
            return await ctx.reply("⚠️ You already have voted to skip this source.")

        Current["context"]["skip_votes"].append(ctx.author.id)

        await Current.setContext(Current["context"])

        await ctx.reply("✅ You have voted to skip this source.")

        channel = await self.Bot.fetch_channel(ctx.voice_client.channel_id)

        if len(Current["context"]["skip_votes"]) >= round(
                (len(channel.members) - 1) / 2
        ):
            await ctx.send(
                "More than half of the votes for skipping music, skipping the source."
            )

            await ctx.voice_client.skip()

    @commands.command()
    async def stop(self, ctx):
        """Stop the player and clear the queue."""

        if not ctx.voice_client:
            return await ctx.reply("I'm not playing anything.")

        await ctx.voice_client.destroy()
        await ctx.reply("Stopped the player and cleared the queue.")

    @commands.command()
    async def seek(self, ctx, offset: int):
        """Seek the source."""

        if not ctx.voice_client:
            return await ctx.reply("I'm not playing anything.")

        Current = await ctx.voice_client.getCurrent()

        if not 0 < offset < Current.duration:
            return await ctx.reply(
                f"Please enter the value between 0 and {Current.duration}."
            )

        await ctx.voice_client.seek(offset)

        await ctx.reply(f"Seeked to {offset}")

    @commands.command(aliases=["vol"])
    async def volume(self, ctx, volume: int):
        """Change the volume."""

        if not ctx.voice_client:
            return await ctx.reply("I'm not playing anything.")

        if not 0 < volume < 101:
            return await ctx.reply("Please enter the value between 1 and 100.")

        await ctx.voice_client.setVolume(volume / 100)
        await ctx.reply(f"Set the volume to {volume}%")

    @commands.command(aliases=["eq"])
    async def equalizer(self, ctx, preset: str = None):
        """Change the equalizer preset."""

        if not ctx.voice_client:
            return await ctx.send("I'm not playing anything.")

        PRESETS = {
            "POP": {
                63: 0.0,
                125: 0.0,
                250: 0.0,
                500: 0.0,
                1000: 2.0,
                2000: 2.0,
                4000: 3.5,
                8000: -2.0,
                16000: -4.0,
            },
            "CLASSIC": {
                63: 0.0,
                125: 0.0,
                250: -1.0,
                500: -6.0,
                1000: 0.0,
                2000: 1.0,
                4000: 1.0,
                8000: 0.0,
                16000: 6.0,
            },
            "JAZZ": {
                63: 0.0,
                125: 0.0,
                250: 2.5,
                500: 5.0,
                1000: -6.0,
                2000: -2.0,
                4000: -1.0,
                8000: 2.0,
                16000: -1.0,
            },
            "ROCK": {
                63: 0.0,
                125: 0.0,
                250: 1.0,
                500: 3.0,
                1000: -10.0,
                2000: -2.0,
                4000: -1.0,
                8000: 3.0,
                16000: 3.0,
            },
            "FLAT": {
                63: 0.0,
                125: 0.0,
                250: 0.0,
                500: 0.0,
                1000: 0.0,
                2000: 0.0,
                4000: 0.0,
                8000: 0.0,
                16000: 0.0,
            },
        }

        selectedPreset = PRESETS.get(preset.upper() if preset else None)

        if not selectedPreset:
            return await ctx.reply(
                f"Invalid preset. Valid presets are{NEWLINE * 2}{NEWLINE.join(PRESETS.keys())}"
            )

        State = await ctx.voice_client.getState()

        State["options"]["filter"]["anequalizer"] = "|".join(
            [
                f"c0 f={Frequency} w=100 g={Gain}|c1 f={Frequency} w=100 g={Gain}"
                for Frequency, Gain in selectedPreset.items()
                if Gain != 0
            ]
        )

        await ctx.voice_client.setFilter(State["options"]["filter"])
        await ctx.reply(f"Changed equalizer preset to {preset}")

    @commands.command(aliases=["q"])
    async def queue(self, ctx):
        """Show the players queue."""

        if not ctx.voice_client:
            return await ctx.reply("I'm not playing anything.")

        if not ctx.voice_client.Queue:
            return await ctx.invoke(self.nowplaying)  # TODO

        def callback(position):
            start = position * 8

            return {
                "embed": discord.Embed(
                    title="Queue",
                    description=NEWLINE.join(
                        map(
                            lambda x: f"{x[0]}. {x[1].title}",
                            itertools.islice(
                                enumerate(ctx.voice_client.Queue, 1), start, start + 8
                            ),
                        )
                    ),
                )
            }

        await self.Bot.pagination(
            ctx, callback, limit=math.floor(len(ctx.voice_client.Queue) / 8)
        )

    @commands.command(aliases=["np"])
    async def nowplaying(self, ctx):
        """Show the current playing."""

        if not ctx.voice_client:
            return await ctx.reply("I'm not playing anything.")

        if not ctx.voice_client.current:
            embed = discord.Embed(title="I'm not playing anything!")
        else:
            Chapters = list(
                filter(
                    lambda x: x["start_time"]
                              <= ctx.voice_client.current.position
                              < x["end_time"],
                    ctx.voice_client.current.get("chapters") or [],
                )
            )
            Chapter = Chapters[0] if Chapters else None

            STATE_EMOJI = {"playing": "▶️", "paused": "⏸️", "stopped": "⏹️"}

            embed = discord.Embed(
                title=ctx.voice_client.current.title,
                url=ctx.voice_client.current.webpage_url,
                description=(
                        (
                            f"- `[{formatDuration(Chapter['start_time'])} ~ {formatDuration(Chapter['end_time'])}]` **{Chapter['title']}**\n\n"
                            if Chapter
                            else ""
                        )
                        + f"> ❤️ Audio Node: **{ctx.voice_client.Node.region}**\n"
                        + f"{STATE_EMOJI[ctx.voice_client.state]} "
                        + getProgress(
                    ctx.voice_client.current.position, ctx.voice_client.duration
                )
                        + f" `[{formatDuration(ctx.voice_client.current.position)}/{formatDuration(ctx.voice_client.current.duration)}]`"
                        + f" 🔉 **{round(ctx.voice_client.volume * 100)}%**"
                ),
            )
            if ctx.voice_client.current.thumbnail:
                embed.set_thumbnail(url=ctx.voice_client.current.thumbnail)

            embed.set_footer(
                text=f"From {ctx.voice_client.current.uploader} | {len(ctx.voice_client.Queue)} sources left"
            )

        embed.colour = ctx.guild.me.colour

        await ctx.reply(embed=embed)

    @commands.command(aliases=["subtitle", "lyrics"])
    async def subtitles(self, ctx, value: str = None):
        """Print the synced subtitle of the currently playing source."""
        usableSubtitles = (
            ctx.voice_client.current.get("subtitles", {}).keys()
            if ctx.voice_client.current
            else []
        )

        if not value:
            return await ctx.reply(
                f"> Usable subtitles: {' '.join(map(lambda x: f'`{x}`', usableSubtitles))}"
            )

        if value and value not in usableSubtitles:
            return await ctx.reply(
                f"> ❎  Couldn't find `{value}` subtitle.\n> \n> Usable subtitles: {' '.join(map(lambda x: f'`{x}`', usableSubtitles))}"
            )

        await ctx.voice_client.getSubtitle(
            lang=value, callback=SubtitleCallback(ctx.channel).callback
        )

        await ctx.reply(f"> ➡️  I'll send {f'`{value}` ' if value else ''} subtitle!")
