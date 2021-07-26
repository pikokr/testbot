from discord.ext import commands
import config

bot = commands.Bot(command_prefix=config.PREFIX)

bot.load_extension('jishaku')

bot.run(config.TOKEN)
