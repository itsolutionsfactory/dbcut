# -*- coding: utf-8 -*-
import logging
import re
import shutil
import sys
import time
from functools import update_wrapper

import click
from dotenv import find_dotenv, load_dotenv
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url

from ..database import Database
from ..utils import cached_property, expand_env_variables, pickle_copy, reraise

magenta = lambda x, **kwargs: click.style("%s" % x, fg="magenta", **kwargs)  # noqa
yellow = lambda x, **kwargs: click.style("%s" % x, fg="yellow", **kwargs)  # noqa
green = lambda x, **kwargs: click.style("%s" % x, fg="green", **kwargs)  # noqa
cyan = lambda x, **kwargs: click.style("%s" % x, fg="cyan", **kwargs)  # noqa
blue = lambda x, **kwargs: click.style("%s" % x, fg="blue", **kwargs)  # noqa
red = lambda x, **kwargs: click.style("%s" % x, fg="red", **kwargs)  # noqa


CONTEXT_SETTINGS = dict(auto_envvar_prefix="dbcut", help_option_names=["-h", "--help"])


class Context(object):
    def __init__(self):
        self.flags = [
            "debug",
            "verbose",
            "quiet",
            "force_yes",
            "dump_sql",
            "export_json",
            "drop_db",
            "force_refresh",
            "last_only",
            "no_cache",
            "profiler",
            "interactive",
            "estimate",
            "with_cache",
        ]
        for flag in self.flags:
            setattr(self, flag, False)
        self.only_tables = []
        self._log_configured = False
        self.is_tty = sys.stdout.isatty()
        self.tty_columns, self.tty_rows = shutil.get_terminal_size(fallback=(80, 24))
        load_dotenv(dotenv_path=find_dotenv(usecwd=True))

    @cached_property
    def dest_db_uri(self):
        destination_uri = expand_env_variables(
            self.config["databases"]["destination_uri"]
        )
        return make_url(destination_uri)

    @cached_property
    def src_db_uri(self):
        source_uri = expand_env_variables(self.config["databases"]["source_uri"])
        return make_url(source_uri)

    @cached_property
    def dest_db(self):
        self.src_db.reflect()
        return Database(
            uri=self.dest_db_uri,
            echo_sql=self.dump_sql,
            cache_dir=self.config["cache"],
            enable_cache=False,
            metadata=pickle_copy(self.src_db.metadata),
        )

    @cached_property
    def src_db(self):
        return Database(
            uri=self.src_db_uri,
            echo_sql=False,
            cache_dir=self.config["cache"],
            enable_cache=(not self.no_cache),
        )

    def configure_log(self):
        if self._log_configured:
            return
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

        self._log_configured = True

    def log(self, *args, **kwargs):
        """Logs a message to stderr."""
        kwargs.setdefault("file", sys.stderr)
        quietable = kwargs.pop("quietable", False)
        if quietable and self.quiet:
            return
        prefix = kwargs.pop("prefix", "")
        tty_truncate = kwargs.pop("tty_truncate", False)
        for msg in args:
            message = "\n".join(prefix + m for m in msg.split("\n"))
            if self.debug:
                message = message.replace("\r", "")
                kwargs["nl"] = True
            if tty_truncate:
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

    def switch_flag(self, flag_name):
        if getattr(self, flag_name, None) is False:
            setattr(self, flag_name, True)
            if flag_name == "interactive":
                setattr(self, "force_yes", False)
            elif flag_name == "force_yes":
                setattr(self, "interactive", False)
            elif flag_name == "debug":
                setattr(self, "verbose", True)
                setattr(self, "quiet", False)
            elif flag_name == "verbose":
                setattr(self, "quiet", False)
            elif flag_name == "quiet":
                setattr(self, "verbose", False)

    def update_options(self, **kwargs):
        for name, value in kwargs.items():
            if name in self.flags:
                if value:
                    self.switch_flag(name)
            elif name == "only_tables":
                for tables_value in value:
                    self.only_tables.extend(tables_value.split(","))
                self.only_tables = list(set(self.only_tables))
            else:
                setattr(self, name, value)

        self.configure_log()

    def handle_error(self):
        exc_type, exc_value, tb = sys.exc_info()
        if isinstance(exc_value, (click.ClickException, click.Abort)) or self.debug:
            reraise(exc_type, exc_value, tb.tb_next)
        else:
            sys.stderr.write(u"\nError: %s\n" % exc_value)
            sys.exit(1)


def make_pass_decorator(context_klass, ensure=True):
    def decorator(f):
        @click.pass_context
        def new_func(*args, **kwargs):
            ctx = args[0]
            if ensure:
                obj = ctx.ensure_object(context_klass)
            else:
                obj = ctx.find_object(context_klass)
            obj.update_options(**kwargs)
            try:
                return ctx.invoke(f, obj, *args[1:], **kwargs)
            except:
                obj.handle_error()

        return update_wrapper(new_func, f)

    return decorator


pass_context = make_pass_decorator(Context)


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


def profiler_option():
    def decorator(f):
        try:
            import easy_profile  # noqa

            click.option(
                "--profiler",
                is_flag=True,
                default=False,
                help="Enables queries profiling.",
            )(f)
        except:
            pass
        return f

    return decorator


def global_options(default_quiet=False):
    def decorator(f):

        options = [
            click.option(
                "--verbose", is_flag=True, default=False, help="Enables verbose output."
            ),
            click.option(
                "--debug", is_flag=True, default=False, help="Enables debug mode."
            ),
            click.option(
                "--quiet",
                "--no-quiet",
                is_flag=True,
                default=default_quiet,
                help="Suppresses most warning and diagnostic messages.",
            ),
            click.option(
                "-i",
                "--interactive",
                is_flag=True,
                default=False,
                help="Prompts for user intervention.",
            ),
            click.option(
                "-y",
                "--force-yes",
                is_flag=True,
                default=False,
                help="Never prompts for user intervention",
            ),
        ]
        for option in options:
            option(f)
        return f

    return decorator
