from discord import Color
from discord.ext import commands

from .utils import checks


class CogManager(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @checks.has_permissions(administrator=True)
    async def load(self, ctx, *, module):
        """Loads a module."""
        await ctx.message.delete(delay=5.0)
        try:
            self.bot.load_extension(module)
        except commands.ExtensionError as e:
            await ctx.send_embed(f'{e.__class__.__name__}: {e}', color=Color.red(), delete_after=5.0)
        else:
            await ctx.send_embed(f'{module} loaded successfully', color=Color.green(), delete_after=5.0)

    @commands.command()
    @checks.has_permissions(administrator=True)
    async def unload(self, ctx, *, module):
        """Unloads a module."""
        await ctx.message.delete(delay=5.0)
        try:
            self.bot.unload_extension(module)
        except commands.ExtensionError as e:
            await ctx.send_embed(f'{e.__class__.__name__}: {e}', color=Color.red(), delete_after=5.0)
        else:
            await ctx.send_embed(f'{module} unloaded successfully', color=Color.green(), delete_after=5.0)

    @commands.group(name='reload', invoke_without_command=True)
    @checks.has_permissions(administrator=True)
    async def _reload(self, ctx, *, module):
        """Reloads a module."""
        await ctx.message.delete(delay=5.0)
        try:
            self.bot.reload_extension(module)
        except commands.ExtensionError as e:
            await ctx.send_embed(f'{e.__class__.__name__}: {e}', color=Color.red(), delete_after=5.0)
        else:
            await ctx.send_embed(f'{module} reloaded successfully', color=Color.green(), delete_after=5.0)

    @_reload.command(name='all', hidden=True)
    @checks.has_permissions(administrator=True)
    async def _reload_all(self, ctx):
        """Reloads all modules"""
        output = ""

        for module in list(self.bot.extensions.keys()):
            try:
                self.bot.reload_extension(module)
            except commands.ExtensionError as e:
                output += f'{module} - {e.__class__.__name__}: {e}\n'
            else:
                output += f'{module} - reloaded successfully\n'

        await ctx.message.delete(delay=5.0)
        await ctx.send_embed(output, delete_after=5.0)

    @commands.command()
    @checks.has_permissions(administrator=True)
    async def cogs(self, ctx):
        await ctx.send_embed(" **»** " + "\n **»** ".join(self.bot.cogs))

    @commands.command(aliases=["extentions"])
    @checks.has_permissions(administrator=True)
    async def extensions(self, ctx):
        await ctx.send_embed(" **»** " + "\n **»** ".join(self.bot.extensions))


def setup(bot):
    bot.add_cog(CogManager(bot))
