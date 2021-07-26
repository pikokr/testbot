from discord.ext import commands
from jishaku import codeblocks, paginators

from client import Client


class Coding(commands.Cog):
    def __init__(self, bot: Client):
        self.bot = bot

    @commands.command('code')
    async def code(self, ctx: commands.Context, *, code: str):
        cb = codeblocks.codeblock_converter(code)
        if cb.language is None:
            return await ctx.reply('코드블럭쓰세요')
        res = await self.bot.piston.execute(cb.language, cb.content)
        pg = paginators.WrappedPaginator(prefix=f'```{cb.language}', suffix='```', max_size=1985)

        pg.add_line(res.output)

        pgi = paginators.PaginatorInterface(ctx.bot, pg, owner=ctx.author)

        return await pgi.send_to(ctx)
