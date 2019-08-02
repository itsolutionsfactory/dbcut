# -*- coding: utf-8 -*-
import os

import click
from tabulate import tabulate

from ..configuration import Configuration
from .context import Context, make_pass_decorator
from .operations import inspect_db, sync_db

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
@click.option(
    "-k",
    "--keep-db",
    "keep_db",
    is_flag=True,
    default=False,
    help="Preserve existing database",
)
@click.option(
    "--force-refresh",
    "force_refresh",
    is_flag=True,
    default=False,
    help="Force refrech all cached queries",
)
@click.option(
    "-y",
    "--force-yes",
    is_flag=True,
    default=False,
    help="Never prompts for user intervention",
)
@click.version_option()
@click.option("--verbose", is_flag=True, default=False, help="Enables verbose output.")
@click.option("--debug", is_flag=True, default=False, help="Enables debug mode.")
@pass_context
def main(ctx, **kwargs):
    """Extract a lightweight subset of your production DB for development and testing purpose."""
    ctx.update_options(**kwargs)
    ctx.configure_log()
    sync_db(ctx)


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument(
    "config",
    callback=load_configuration_file,
    type=click.Path(writable=False, readable=True),
    required=True,
)
@click.version_option()
@click.option("--verbose", is_flag=True, default=False, help="Enables verbose output.")
@click.option("--debug", is_flag=True, default=False, help="Enables debug mode.")
@pass_context
def inspect(ctx, **kwargs):
    """ Analyze all databases."""
    ctx.update_options(**kwargs)
    rows, headers = inspect_db(ctx)
    click.echo(tabulate(rows, headers=headers))
