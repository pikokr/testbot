from client import Client
from modules.Coding import Coding
from modules.General import General


def setup(bot: Client):
    bot.add_cog(General(bot))
    bot.add_cog(Coding(bot))
