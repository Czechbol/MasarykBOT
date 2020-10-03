import logging
import traceback

from discord.ext import commands

from .utils import constants


log = logging.getLogger(__name__)


class Errors(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def on_command_error(self, ctx, error):
        for ignore_error in [commands.BadArgument, commands.MissingRequiredArgument, commands.MissingRole]:
            if isinstance(error, ignore_error):
                return

        if hasattr(ctx.command, "on_error"):
            return

        if isinstance(error, commands.NoPrivateMessage):
            await ctx.author.send_error('This command cannot be used in private messages.')
            return

        if isinstance(error, commands.MissingPermissions):
            await ctx.send_error("Sorry. You don't have permissions to use this command")
            return

        for just_printable in [commands.ArgumentParsingError, commands.BotMissingPermissions]:
            if isinstance(error, just_printable):
                await ctx.send_error(error)
                return

        if isinstance(error, commands.CommandInvokeError):
            await self.log_error(ctx, ctx.original)
            return

        await self.log_error(ctx, error)

    async def log_error(self, ctx, error):
        command_name = ctx.command.qualified_name
        trace = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        msg = f'In {command_name}:\n{trace}'

        log.error(msg)

        for channel_id in constants.error_log_channels:
            if (channel := self.bot.get_channel(channel_id)) is not None:
                for i in range(0, len(msg), 1900):
                    chunk = msg[i:i+1900]
                    await channel.send(f"```\n{chunk}\n```")

def setup(bot):
    bot.add_cog(Errors(bot))