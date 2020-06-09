from discord import Color, Embed
from discord.ext import commands
import time
import logging

import ast
from astpretty import pprint
import re

import multiprocessing
import os


class EvalError(Exception):
    pass


class Evaluator:
    allowed_imports = [
        "math", "string", "datetime", "random"
    ]

    allowed_builtins = {
        'abs': abs, 'all': all, 'any': any, 'bin': bin, 'bool': bool,
        'chr': chr, 'dict': dict, 'divmod': divmod, 'enumerate': enumerate,
        'filter': filter, 'float': float, 'format': format,
        'frozenset': frozenset, 'hash': hash, 'hex': hex, 'id': id,
        'int': int, 'isinstance': isinstance, 'iter': iter, 'len': len,
        'list': list, 'map': map, 'max': max, 'min': min, 'next': next,
        'object': object, 'oct': oct, 'ord': ord, 'pow': pow, 'range': range,
        'repr': repr, 'reversed': reversed, 'round': round, 'set': set,
        'slice': slice, 'sorted': sorted, 'str': str, 'sum': sum,
        'tuple': tuple, 'zip': zip, 'Exception': Exception,
        '__import__': __import__
    }

    def __init__(self, filename=None):
        self.allowed_builtins["print"] = self.print

        if filename is None:
            import tempfile
            self.filename = tempfile.NamedTemporaryFile(delete=False).name
        else:
            self.filename = filename

    def print(self, *args, sep=" ", end="\n", file=None, flush=None):
        with open(self.filename, "a") as f:
            f.write(sep.join(map(str, args)) + end)
            f.flush()

    class Transformer(ast.NodeTransformer):
        def __init__(self, evaluator):
            self.evaluator = evaluator
            print(type(self.evaluator), self.evaluator)

        def check_illegal(self, text):
            if re.match("__([^_]+)__", text):
                raise EvalError("unsuported __name__")
            if re.match("_([^_]+)", text):
                raise EvalError("unsuported _name")

        def visit_Import(self, node):
            for name in map(lambda imp: imp.name, node.names):
                if name not in Evaluator.allowed_imports:
                    self.check_illegal(name)
            return node

        def visit_ImportFrom(self, node):
            if node.module not in Evaluator.allowed_imports:
                raise EvalError("unsuported import")
            for alias in node.names:
                for name in [alias.name, alias.asname]:
                    self.check_illegal(name)

            return node

        def visit_Attribute(self, node):
            self.check_illegal(node.attr)
            return node

        def visit_Name(self, node):
            self.check_illegal(node.id)
            return node

        def visit_Str(self, node):
            self.check_illegal(node.s)
            return node

        def visit_Index(self, node):
            (retval, printval) = self.evaluator._eval(ast.Expression(node.value))
            self.check_illegal(retval)
            return node

        def visit_Call(self, node):
            for arg in node.args:
                (retval, printval) = self.evaluator._eval(ast.Expression(arg))
                self.check_illegal(retval)
            return node

    def _eval(self, tree, verbose=False):
        self.Transformer(self).visit(tree)
        tree = ast.fix_missing_locations(tree)

        if verbose:
            pprint(tree)

        co = compile(tree, filename="<ast>", mode="eval")
        retval = eval(co, {'__builtins__': self.allowed_builtins}, {})

        with open(self.filename, "r") as f:
            retval = retval, f.read()
        os.remove(self.filename)

        return retval

    def _exec(self, tree, verbose=False):
        self.Transformer(self).visit(tree)
        tree = ast.fix_missing_locations(tree)

        if verbose:
            pprint(tree)

        co = compile(tree, filename="<ast>", mode="exec")
        exec(co, {'__builtins__': self.allowed_builtins}, {})

        with open(self.filename, "r") as f:
            retval = None, f.read()
        os.remove(self.filename)

        return retval

    def run(self, code, verbose=False):
        with multiprocessing.Pool(processes=1) as pool:
            try:
                tree = ast.parse(code)
                result = pool.apply_async(self._exec, [tree, verbose])
                (retval, printval) = result.get(timeout=5)
                return 0, printval

            except EvalError as e:
                return 1, str(e)

            except multiprocessing.TimeoutError:
                return 1, "Timeout: exceeded 5 seconds"

            except Exception as e:
                return 1, str(e)


class Eval(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log = logging.getLogger(__name__)

    async def eval_coro(self, code):
        evaluator = Evaluator()
        return evaluator.run(code)

    @commands.command(name='eval')
    async def _eval(self, ctx, *, body):
        """
        check if the body is executable
        check for blocked_words which could be potentionally harmful

        format embed in format
            ``` code ```
            Finished in: 00:00:00

        set color and reaction depending on success / error

        remove play reaction so the code can't be executed
        again
        """
        if not self.is_evaluatable_message(body):
            return

        blocked_words = ['os', 'sys', 'multiprocessing',
                         'env', 'subprocess', 'open', 'token']

        for x in blocked_words:
            if x.lower() in body.lower():
                embed = Embed(color=Color.red())
                embed.add_field(
                    name="Error", value=f'```\nYour code contains certain blocked words.\n```')
                embed.set_footer(icon_url=ctx.author.avatar_url)
                return await ctx.send(embed=embed)

        body = self.cleanup_code(body)
        embed = Embed(color=Color(0xffffcc))

        time_start = time.time()
        ret_code, value = await self.eval_coro(body)
        time_end = time.time()

        elapsed_time = time.strftime(
            "%H:%M:%S", time.gmtime(time_end - time_start))

        out = err = None
        if ret_code == 0:
            dots = "..." if len(value) > 1000 else ""
            embed.add_field(
                name="Output",
                value=f'```py\n{value[:1000]}{dots}\n```')
            embed.set_footer(
                text=f"Finished in: {elapsed_time}",
                icon_url=ctx.author.avatar_url)

            out = await ctx.send(embed=embed)

        else:
            embed.color = Color.red()
            embed.add_field(
                name="Error",
                value=f'```\n{value}\n```')
            embed.set_footer(
                text=f"Finished in: {elapsed_time}",
                icon_url=ctx.author.avatar_url)

            err = await ctx.send(embed=embed)

        if out:
            await ctx.message.add_reaction('\u2705')  # tick
        elif err:
            await ctx.message.add_reaction('\u2049')  # x
        else:
            await ctx.message.add_reaction('\u2705')

        await ctx.message.remove_reaction("▶", ctx.author)
        await ctx.message.remove_reaction("▶", self.bot.user)

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    def get_syntax_error(self, e):
        if e.text is None:
            return f'```py\n{e.__class__.__name__}: {e}\n```'
        return f'```py\n{e.text}{"^":>{e.offset}}\n{e.__class__.__name__}: {e}```'

    def is_evaluatable_message(self, body):
        return (body.startswith("```py") and
                body.endswith("```") and
                body.count("\n") >= 2 and
                len(self.cleanup_code(body)) > 0)

    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.is_evaluatable_message(message.content):
            return

        if message.author.bot:
            return

        await message.add_reaction("▶")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """
        check if users clicked the play button on executable code
        the bot has to be a reactor on the executable message
        """
        message = reaction.message
        if not self.is_evaluatable_message(message.content):
            return

        if message.author.bot or user.bot or message.author != user:
            return

        if str(reaction.emoji) != "▶":
            return

        if self.bot.user not in await reaction.users().flatten():
            return

        self.log.info(f"{user} has reacted on message code message")

        ctx = commands.Context(prefix=self.bot.command_prefix, guild=message.guild,
                               channel=message.channel, message=message, author=user)
        await self._eval.callback(self, ctx, body=message.content)


def setup(bot):
    bot.add_cog(Eval(bot))
