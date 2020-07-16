from discord.ext import commands
from discord.utils import get, find

import logging

from .utils import constants, checks


log = logging.getLogger(__name__)


class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    @checks.has_permissions(manage_roles=True)
    async def on_ready(self):
        await self._synchronize()

    async def _synchronize(self):
        for guild in self.bot.guilds:
            await self._synchronize_guild(guild)

    async def _synchronize_guild(self, guild):
        verified_role = find(lambda role: role.id in constants.verified_roles, guild.roles)

        for channel_id in constants.verification_channels:
            channel = get(guild.channels, id=channel_id)
            if channel is None:
                continue

            async for message in channel.history():
                verif_react = find(lambda reaction: reaction.emoji.name.lower() in ("verification", "verify", "accept"), message.reactions)
                if verif_react is None:
                    continue

                with_role = set(filter(lambda member: verified_role in member.roles, guild.members))
                verified = set(await verif_react.users().flatten())

                log.info(f"found {len(with_role - verified) + len(verified - with_role)} users out of sync with the verification system")

                for member in (with_role - verified):
                    await self._verify_leave(member)

                for member in (verified - with_role):
                    await self._verify_join(member)

    @commands.Cog.listener()
    @checks.has_permissions(manage_roles=True)
    async def on_raw_reaction_add(self, payload):
        await self.on_raw_reaction_update(payload)

    @commands.Cog.listener()
    @checks.has_permissions(manage_roles=True)
    async def on_raw_reaction_remove(self, payload):
        await self.on_raw_reaction_update(payload)

    async def on_raw_reaction_update(self, payload):
        if payload.channel_id not in constants.verification_channels:
            return

        if payload.emoji.name.lower() not in ("verification", "verify", "accept"):
            return

        guild = get(self.bot.guilds, id=payload.guild_id)
        member = get(guild.members, id=payload.user_id)

        if payload.event_type == "REACTION_ADD":
            await self._verify_join(member)

        elif payload.event_type == "REACTION_REMOVE":
            await self._verify_leave(member)

    async def _verify_join(self, member):
        verified_role = find(lambda role: role.id in constants.verified_roles, member.guild.roles)
        await member.add_roles(verified_role)
        log.info(f"verified user {member.name}, added role @{verified_role}")

    async def _verify_leave(self, member):
        to_remove = list(filter(lambda role: role.id in (constants.verified_roles + list(constants.about_you_roles.keys())), member.roles))
        await member.remove_roles(*to_remove)
        log.info(f"unverified user {member.name}, removed roles {', '.join(map(lambda r: '@'+r.name, to_remove))}")


def setup(bot):
    bot.add_cog(Verification(bot))
