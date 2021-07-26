from client import Client
from modules.Audio import Audio
from modules.Coding import Coding
from modules.General import General


def setup(bot: Client):
    bot.add_cog(General(bot))
    bot.add_cog(Coding(bot))
    bot.add_cog(Audio(bot))
