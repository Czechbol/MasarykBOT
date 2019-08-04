from discord.ext import commands
import asyncio
import discord

from core.utils import db
from core.utils.db import Database

from config import BotConfig


class Context(commands.Context):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            self.db = Database.connect(**BotConfig.db_config)
        except db.DatabaseConnectionError as e:
            self.db = None
