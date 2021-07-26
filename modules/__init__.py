from discord.ext import commands

from modules.General import General


def setup(bot: commands.Bot):
    bot.add_cog(General(bot))
