import asyncio
import contextlib

import discord
from discord.ext import commands
from discord.ext.commands import CommandNotFound
from jishaku import paginators
from pyston import PystonClient
import traceback
import discodo
import config


class Client(commands.Bot):
    piston = PystonClient()

    # wavelink: wavelink.Client

    def __init__(self, command_prefix, **options):
        super().__init__(command_prefix, **options)
        self.Audio = discodo.DPYClient(self)
        self.Audio.registerNode(host=config.DISCODO_HOST, port=config.discodo['PORT'], password=config.discodo['PASSWORD'])

    async def pagination(self, ctx, callback, limit):
        position = 0

        message = await ctx.reply(**callback(position))

        async def _add_emojis():
            with contextlib.suppress(Exception):
                for emoji in ["◀", "⏹", "▶"]:
                    await message.add_reaction(emoji)

        self.loop.create_task(_add_emojis())

        while not self.is_closed():
            try:
                reaction, user = await self.wait_for(
                    "reaction_add",
                    check=lambda reaction, user: user == ctx.author
                                                 and reaction.message.id == message.id
                                                 and reaction.emoji in ["◀", "⏹", "▶"],
                    timeout=30,
                )
            except asyncio.TimeoutError:
                with contextlib.suppress(Exception):
                    await message.clear_reactions()
                break

            if reaction.emoji == "◀" and position > 0:
                position -= 1
            elif reaction.emoji == "⏹":
                with contextlib.suppress(Exception):
                    await message.clear_reactions()
                break
            elif reaction.emoji == "▶" and position < limit:
                position += 1

            await message.edit(**callback(position))

            with contextlib.suppress(discord.Forbidden):
                await message.remove_reaction(reaction.emoji, user)

    async def on_command_error(self, ctx: commands.Context, exception: Exception):
        if isinstance(exception, CommandNotFound):
            return
        pg = paginators.WrappedPaginator(prefix='```', suffix='```', max_size=1985)

        pg.add_line(
            '\n'.join(traceback.format_exception(etype=type(exception), value=exception, tb=exception.__traceback__)))

        pgi = paginators.PaginatorInterface(ctx.bot, pg, owner=ctx.author)

        return await pgi.send_to(ctx)
