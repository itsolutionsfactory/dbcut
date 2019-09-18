# -*- coding: utf-8 -*-
import logging
import re
import shutil
import sys
import time
from functools import update_wrapper

import click
from sqlalchemy import event
from sqlalchemy.engine import Engine

from ..database import Database
from ..utils import cached_property

magenta = lambda x, **kwargs: click.style("%s" % x, fg="magenta", **kwargs)  # noqa
yellow = lambda x, **kwargs: click.style("%s" % x, fg="yellow", **kwargs)  # noqa
green = lambda x, **kwargs: click.style("%s" % x, fg="green", **kwargs)  # noqa
cyan = lambda x, **kwargs: click.style("%s" % x, fg="cyan", **kwargs)  # noqa
blue = lambda x, **kwargs: click.style("%s" % x, fg="blue", **kwargs)  # noqa
red = lambda x, **kwargs: click.style("%s" % x, fg="red", **kwargs)  # noqa


class Context(object):
    def __init__(self):
        self.debug = False
        self.verbose = True
        self.force_yes = False
        self.dump_sql = False
        self.export_json = False
        self.drop_db = False
        self.force_refresh = False
        self.last_only = False
        self.no_cache = False
        self.profiler = False
        self.interactive = False
        self.is_tty = sys.stdout.isatty()
        self.tty_columns, self.tty_rows = shutil.get_terminal_size(fallback=(80, 24))

    @cached_property
    def dest_db(self):
        return Database(
            uri=self.config["databases"]["destination_uri"], echo_sql=self.dump_sql
        )

    @cached_property
    def src_db(self):
        return Database(uri=self.config["databases"]["source_uri"])

    def configure_log(self):
        logging.basicConfig()
        self.logger = logging.getLogger("dbcut.cli")

        if not self.verbose:
            self.logger.setLevel(logging.INFO)
            return

        self.logger.setLevel(logging.DEBUG)

        for handler in self.logger.root.handlers:
            handler.setFormatter(AnsiColorFormatter())

        @event.listens_for(Engine, "before_cursor_execute")
        def before_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            conn.info.setdefault("query_start_time", []).append(time.time())
            self.logger.debug("Start Query on %s: \n%s\n" % (conn.engine, statement))

        @event.listens_for(Engine, "after_cursor_execute")
        def after_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            total = time.time() - conn.info["query_start_time"].pop(-1)
            self.logger.debug("Query Complete!")
            self.logger.debug("Total Time: %f" % total)

    def log(self, *args, **kwargs):
        """Logs a message to stderr."""
        kwargs.setdefault("file", sys.stderr)
        prefix = kwargs.pop("prefix", "")
        for msg in args:
            message = prefix + msg
            if self.debug:
                message = message.replace("\r", "")
                kwargs["nl"] = True
            if self.is_tty:
                message = "\n".join(
                    msg[: self.tty_columns] for msg in message.split("\n")
                )
            if not self.dump_sql:
                click.echo(message, **kwargs)

    def confirm(self, message, **kwargs):
        kwargs.setdefault("abort", True)
        if not self.force_yes:
            return click.confirm(message, **kwargs)

    def continue_operation(self, message, **kwargs):
        if not self.interactive:
            return True
        kwargs.setdefault("abort", False)
        return click.confirm(message, **kwargs)

    def update_options(self, **kwargs):
        self.__dict__.update(kwargs)
        if self.debug and not self.verbose:
            self.verbose = True
        if self.interactive:
            self.force_yes = False
        if self.dump_sql:
            self.interactive = False
        self.configure_log()


def make_pass_decorator(context_klass, ensure=True):
    def decorator(f):
        @click.pass_context
        def new_func(*args, **kwargs):
            ctx = args[0]
            if ensure:
                obj = ctx.ensure_object(context_klass)
            else:
                obj = ctx.find_object(context_klass)
            return ctx.invoke(f, obj, *args[1:], **kwargs)

        return update_wrapper(new_func, f)

    return decorator


re_color_codes = re.compile(r"\033\[(\d;)?\d+m")


class AnsiColorFormatter(logging.Formatter):

    LEVELS = {
        "WARNING": red(" WARN"),
        "INFO": blue(" INFO"),
        "DEBUG": blue("DEBUG"),
        "CRITICAL": magenta(" CRIT"),
        "ERROR": red("ERROR"),
    }

    def __init__(self, msgfmt=None, datefmt=None):
        logging.Formatter.__init__(self, None, "%H:%M:%S")

    def format(self, record):
        """
        Format the specified record as text.

        The record's attribute dictionary is used as the operand to a
        string formatting operation which yields the returned string.
        Before formatting the dictionary, a couple of preparatory steps
        are carried out. The message attribute of the record is computed
        using LogRecord.getMessage(). If the formatting string contains
        "%(asctime)", formatTime() is called to format the event time.
        If there is exception information, it is formatted using
        formatException() and appended to the message.
        """
        message = record.getMessage()
        asctime = self.formatTime(record, self.datefmt)
        name = yellow(record.name)

        s = "%(timestamp)s %(levelname)s %(name)s " % {
            "timestamp": green("%s,%03d" % (asctime, record.msecs), bold=True),
            "levelname": self.LEVELS[record.levelname],
            "name": name,
        }

        if "\n" in message:
            indent_length = len(re_color_codes.sub("", s))
            message = message.replace("\n", "\n" + " " * indent_length)

        s += message
        return s
