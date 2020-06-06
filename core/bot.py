import asyncio
import sys
import logging
import os

import discord
from discord import Color, Embed, Game
from discord.ext.commands import Bot

import traceback
import datetime
import json

from core.utils import context, db
from core.utils.db import Database


class MasarykBot(Bot):
    def __init__(self, *args, activity=Game(name=f"Commands: {os.getenv('PREFIX')}help"), **kwargs):
        super().__init__(*args, **kwargs)

        self.ininial_params = args, kwargs
        self.default_activity = activity

        self.setup_logging()
        self.loop.create_task(self.handle_database())

        self.readyCogs = {}

    """--------------------------------------------------------------------------------------------------------------------------"""

    def setup_logging(self):
        """
        sets up custom logging into self.log variable

        set format to
        [2019-09-29 18:51:04] [INFO   ] core.logger: Begining backup
        """

        log = logging.getLogger()
        log.setLevel(logging.INFO)

        dt_fmt = '%Y-%m-%d %H:%M:%S'
        fmt = logging.Formatter(
            '[{asctime}] [{levelname:<7}] {name}: {message}', dt_fmt, style='{')

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(fmt)
        log.addHandler(handler)

        self.log = log

    """--------------------------------------------------------------------------------------------------------------------------"""

    async def handle_database(self):
        """
        create a database connection
        on database connection
            trigger on_ready event for
            events with @needs_database decorator
        when connection cannot be established
            set presence as dnd
            and retry every 2 seconds
        """

        await self.wait_until_ready()
        await self.change_presence(
            status=discord.Status.offline)

        while True:
            try:
                self.db = await Database.connect()

                self.log.info("[BOT] Database online: connected.")

                await self.trigger_event("on_ready")
                await self.bot_ready()

                break

            except db.DatabaseConnectionError as e:
                self.db = Database()

                self.log.error(e)

                await self.change_presence(status=discord.Status.dnd, activity=Game(name="Database offline"))

                await asyncio.sleep(15)

    async def process_commands(self, message):
        """
        send custom Context instead of the discord API's Context
        """

        ctx = await self.get_context(message, cls=context.Context)

        if ctx.command is None:
            return

        self.log.info("user {} used command: {}".format(message.author, message.content))
        await self.invoke(ctx)

    """--------------------------------------------------------------------------------------------------------------------------"""

    def handle_exit(self):
        """
        finish runnings tasks and logout bot
        """

        self.loop.run_until_complete(self.logout())
        for task in asyncio.Task.all_tasks(loop=self.loop):
            if task.done():
                task.exception()
                continue

            task.cancel()

            try:
                self.loop.run_until_complete(
                    asyncio.wait_for(task, 5, loop=self.loop))
                task.exception()
            except asyncio.InvalidStateError:
                pass
            except asyncio.TimeoutError:
                pass
            except asyncio.CancelledError:
                pass

        if self.db and self.db.pool:
            self.db.pool.close()
            self.loop.run_until_complete(self.db.pool.wait_closed())

    """--------------------------------------------------------------------------------------------------------------------------"""

    def start(self, *args, **kwargs):
        while True:
            try:
                # start the bot
                self.loop.run_until_complete(super().start(*args, **kwargs))
            except SystemExit:
                self.handle_exit()
            except KeyboardInterrupt:
                self.handle_exit()
                self.loop.close()
                print("Bot shut down by KeyboardInterrupt")
                sys.exit(0)

            print("Bot restarting")
            super().__init__(*self.ininial_params[0], **self.ininial_params[1])

    """--------------------------------------------------------------------------------------------------------------------------"""

    async def bot_ready(self):
        """
        wait until all values in self.readyCogs
        are set to True, which means all cogs
        with on_ready event are ready and
        therefore the bot is ready

        example:
            @commands.Cog.listener()
            async def on_ready(self):
                self.bot.readyCogs[self.__class__.__name__] = False

                # ... code here ...

                self.bot.readyCogs[self.__class__.__name__] = True

        """
        await self.wait_until_ready()

        while True:
            await asyncio.sleep(1)
            if all(self.readyCogs.values()) or len(self.readyCogs.values()) == 0:
                break

        self.intorduce()

    """--------------------------------------------------------------------------------------------------------------------------"""

    def intorduce(self):
        bot_name = self.user.name.encode(errors='replace').decode()

        self.log.info("Bot is now all ready to go")
        print("\n\n\n")
        print("""               .,***,.
        /.             *%&*
     #%     /%&&&%            %#
    &   *&&&&&*%     /&&/     &/
   %*  &&&&&&& #&&%         (&&&%&,
   /( %&&&&&&& /(*            .&&&%
    ,%%&&         ....       .&%
      %& *%&&&&&&&&&&&&&&,  ,(.
      (&&&&&&&&&&&&&&%&&&&.   &&
       /&%&%,.*&%&%%&     *&  %&
        %&  ,%. .&,&. *&&  #*
        %&  ,%. .& .&.    (&   (
        (%&(   %&(   *%&&%     &
         &&%  (&  *%(       ,&
          &&&&&% ,&&(  .&   (
          ,&   .**.    ,&   *
           &%*#&&&%.. %&&&(
           /&&&&&/           %
             &&      /  (%&&(
              %% %   #&&&&.
               *&&, ,&&,
                 /&&&.                 \n""")
        print("     [BOT] {0} ready to serve! \n\n\n".format(bot_name))

        self.loop.create_task(self.change_presence(
            activity=self.default_activity))

    """--------------------------------------------------------------------------------------------------------------------------"""

    async def trigger_event(self, event_name, *args, **kwargs):
        """
        trigger on_{event} function in each
        cog. wait until each function finished running

        example:
            # in cog call
            self.bot.trigger_event("message", ctx.message)

            @commands.Cog.listener()
            async def on_message(self, message):
                # gets called
                pass
        """

        events = []
        for cog_name, cog in self.cogs.items():
            event = list(
                map(lambda event: event[1],
                    filter(lambda listener: listener[0] == event_name,
                           cog.get_listeners()))
            )

            events += event

        if hasattr(self, event_name):
            events.append(getattr(self, event_name))

        tasks = []
        for event in events:
            task = self.loop.create_task(event(*args, **kwargs))
            tasks.append(task)

        if len(tasks) != 0:
            await asyncio.wait(tasks)

    """--------------------------------------------------------------------------------------------------------------------------"""

    async def on_error(self, event, *args, **kwargs):
        """
        format python traceback into a more descriptive
        format, put it into an embed and send it
        to error_channels
        """
        exc_type, exc_value, exc_traceback = sys.exc_info()

        exc = traceback.format_exception(
            exc_type, exc_value, exc_traceback, chain=False)

        description = '```py\n%s\n```' % ''.join(exc)
        time = datetime.datetime.utcnow()

        self.log.error(f'Event {event} at {time}: More info: {description}')
