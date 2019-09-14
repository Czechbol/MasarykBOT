import discord
from discord.ext import commands
from discord import Colour, Embed, Member, Object, File

from datetime import datetime, timedelta

import core.utils.get
from core.utils.db import Database
from core.utils.checks import needs_database


class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.in_channels = set()
        self.users_on_cooldown = {}

    """---------------------------------------------------------------------------------------------------------------------------"""

    @commands.command()
    async def add_verification_message(self, ctx, message_id: int):
        self.in_channels.add(message_id)

    """---------------------------------------------------------------------------------------------------------------------------"""

    @needs_database
    async def on_raw_reaction_update(self, payload, event_type: str, *, db: Database = None):
        if (payload.user_id == self.bot.user.id or
                payload.channel_id not in self.in_channels):
            return

        cooldown = self.users_on_cooldown.get(payload.user_id)
        if cooldown and cooldown + timedelta(seconds=1) > datetime.now():
            return  # on cooldown

        # --[]

        await db.execute("""
            SELECT * FROM verification
            WHERE channel_id = %s AND deleted_at IS NULL
            LIMIT 1
        """, (payload.channel_id,))
        row = await db.fetchone()

        channel = self.bot.get_channel(payload.channel_id)
        guild = channel.guild
        role = guild.get_role(row["verified_role_id"])

        author = guild.get_member(payload.user_id)
        if event_type == "REACTION_ADD":
            await author.add_roles(role)
        else:
            await author.remove_roles(role)

        # --[]

        self.users_on_cooldown[payload.user_id] = datetime.now()

    """---------------------------------------------------------------------------------------------------------------------------"""

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        await self.on_raw_reaction_update(payload, event_type="REACTION_ADD")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        await self.on_raw_reaction_update(payload, event_type="REACTION_REMOVE")

    """---------------------------------------------------------------------------------------------------------------------------"""

    @commands.Cog.listener()
    @needs_database
    async def on_ready(self, *, db: Database = None):
        self.bot.readyCogs[self.__class__.__name__] = False

        # load channels into memory for faster checks
        await db.execute("""
            SELECT DISTINCT channel_id, deleted_at
            FROM verification
            WHERE deleted_at IS NULL
        """)
        rows = await db.fetchall()
        self.in_channels = set(row["channel_id"] for row in rows)

        self.bot.readyCogs[self.__class__.__name__] = True


def setup(bot):
    bot.add_cog(Verification(bot))
