# -*- coding: utf-8 -*-

# from functools import update_wrapper

import click

from ..context import global_options, pass_context, profiler_option
from ..operations import load


def load_options():
    def decorator(f):

        options = [
            click.option(
                "--no-cache",
                "no_cache",
                is_flag=True,
                default=False,
                help="Do not use any local cache",
            ),
            click.option(
                "--only",
                "only_tables",
                help="Executes only queries for the given tables",
                multiple=True,
            ),
            click.option(
                "--force-refresh",
                "force_refresh",
                is_flag=True,
                default=False,
                help="Force refresh all cached queries",
            ),
            click.option(
                "-l",
                "--last-only",
                is_flag=True,
                default=False,
                help="Executes only the last query",
            ),
        ]
        for option in options:
            option(f)
        return f

    return decorator


@click.command("load")
@load_options()
@global_options()
@profiler_option()
@pass_context
def cli(ctx, **kwargs):
    """Extract and load data to the target database."""
    load(ctx)
