from discord.ext import commands

from client import Client


class General(commands.Cog):
    def __init__(self, bot: Client):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'Logged in as {self.bot.user}')
