# -*- coding: utf-8 -*-
import os

import click

from ..configuration import Configuration
from .context import Context, make_pass_decorator, profiler_option
from .operations import sync_db

click.disable_unicode_literals_warning = True


CONTEXT_SETTINGS = dict(auto_envvar_prefix="dbcut", help_option_names=["-h", "--help"])


class MigrationContext(Context):
    pass


pass_context = make_pass_decorator(MigrationContext)


def load_configuration_file(ctx, param, value):
    if value is not None:
        if os.path.isfile(value) and os.access(value, os.R_OK):
            return Configuration(value)
        else:
            ctx.fail("File '%s' does not exist" % value)


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument(
    "config",
    callback=load_configuration_file,
    type=click.Path(writable=True, readable=True),
    required=True,
)
@click.option(
    "--dump-sql", is_flag=True, default=False, help="Dumps all sql insert queries."
)
@click.option("--export-json", is_flag=True, default=False, help="Export data to json.")
@click.option(
    "-d",
    "--drop-db",
    "drop_db",
    is_flag=True,
    default=False,
    help="Drop existing database first",
)
@profiler_option()
@click.option(
    "-i",
    "--interactive",
    is_flag=True,
    default=False,
    help="Prompt before every query.",
)
@click.option(
    "--force-refresh",
    "force_refresh",
    is_flag=True,
    default=False,
    help="Force refrech all cached queries",
)
@click.option(
    "--no-cache",
    "no_cache",
    is_flag=True,
    default=False,
    help="Do not use any local cache path",
)
@click.option(
    "-y",
    "--force-yes",
    is_flag=True,
    default=False,
    help="Never prompts for user intervention",
)
@click.option(
    "-l", "--last-only", is_flag=True, default=False, help="Execute only the last query"
)
@click.version_option()
@click.option("--verbose", is_flag=True, default=False, help="Enables verbose output.")
@click.option("--debug", is_flag=True, default=False, help="Enables debug mode.")
@pass_context
def main(ctx, **kwargs):
    """Extract a lightweight subset of your production DB for development and testing purpose."""
    ctx.update_options(**kwargs)
    sync_db(ctx)
