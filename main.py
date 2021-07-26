import config
from client import Client

bot = Client(command_prefix=config.PREFIX, owner_ids=config.OWNERS)

bot.load_extension('jishaku')

bot.load_extension('modules')

bot.run(config.TOKEN)
