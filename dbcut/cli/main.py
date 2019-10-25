# -*- coding: utf-8 -*-
import os
import os.path as op
import sys

import click

from .. import VERSION
from ..configuration import Configuration
from .context import CONTEXT_SETTINGS, global_options, pass_context


class DbcutMultiCommand(click.MultiCommand):
    def list_commands(self, ctx):
        cmd_folder = op.abspath(op.join(op.dirname(__file__), "commands"))
        commands = []
        for filename in os.listdir(cmd_folder):
            if filename.endswith(".py") and filename.startswith("cmd_"):
                commands.append(filename[4:-3])
        order = ["load", "flush", "inspect", "dumpsql", "dumpjson"]
        return sorted(commands, key=lambda x: order.index(x) if x in order else 100)

    def get_command(self, ctx, name):
        if sys.version_info[0] == 2:
            name = name.encode("ascii", "replace")
        if name in self.list_commands(ctx):
            mod = __import__("dbcut.cli.commands.cmd_" + name, None, None, ["cli"])
            return mod.cli


def load_configuration_file(ctx, param, value):
    if value is not None:
        if os.path.isfile(value) and os.access(value, os.R_OK):
            return Configuration(value)
        else:
            ctx.fail("File '%s' does not exist" % value)


@click.command(cls=DbcutMultiCommand, context_settings=CONTEXT_SETTINGS, chain=True)
@click.option(
    "-c",
    "--config",
    callback=load_configuration_file,
    type=click.Path(writable=True, readable=True),
    help="Configuration file",
    default="dbcut.yml",
)
@click.version_option(version=VERSION)
@global_options()
@pass_context
def main(ctx, **kwargs):
    """Extract a lightweight subset of your production DB for development and testing purpose."""
    pass
