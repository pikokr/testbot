from discord.ext import commands
from discord.ext.commands import CommandNotFound
from pyston import PystonClient


class Client(commands.Bot):
    piston = PystonClient()

    async def on_command_error(self, ctx: commands.Context, exception):
        if isinstance(exception, CommandNotFound):
            return
        await ctx.reply(f'```\n{exception}\n```')
