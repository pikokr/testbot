from discord.ext import commands
from discord.ext.commands import CommandNotFound
from jishaku import paginators
from pyston import PystonClient
import traceback
import discodo


class Client(commands.Bot):
    piston = PystonClient()

    # wavelink: wavelink.Client

    def __init__(self, command_prefix, **options):
        super().__init__(command_prefix, **options)
        self.Audio = discodo.DPYClient(self)
        self.Audio.registerNode(region='LOCAL')

    async def on_command_error(self, ctx: commands.Context, exception: Exception):
        if isinstance(exception, CommandNotFound):
            return
        pg = paginators.WrappedPaginator(prefix='```', suffix='```', max_size=1985)

        pg.add_line(
            '\n'.join(traceback.format_exception(etype=type(exception), value=exception, tb=exception.__traceback__)))

        pgi = paginators.PaginatorInterface(ctx.bot, pg, owner=ctx.author)

        return await pgi.send_to(ctx)
