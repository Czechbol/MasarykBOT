from discord import Game
from discord.ext.commands import when_mentioned_or

from core.bot import MasarykBot
from config import BotConfig

from glob import glob
import time

if __name__ == "__main__":
    print()

    bot = MasarykBot(
        command_prefix=when_mentioned_or(BotConfig.prefix),
        case_insensitive=True,
        db_config=BotConfig.db_config
    )

    modules = [
        "core.logger",
        "core.events",
        "core.admin",
        "core.help",

        "cogs.reactionPicker",
        "cogs.leaderboard",
        "cogs.fun"
    ]

    boot_message = """
    Boot sequence initialised

    Seeking cogs...
    {} cogs found

    Loading cogs...""".format(len(modules))

    for letter in boot_message.strip("\n"):
        print(letter, end="")
    print()

    for module in modules:
        bot.load_extension(module)
    print("    Loaded:", ", ".join(bot.cogs.keys()))

    print()
    bot.start(BotConfig.token)
