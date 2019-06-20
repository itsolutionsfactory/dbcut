# -*- coding: utf-8 -*-
import click
import os
from .helpers import Context, cached_property, make_pass_decorator
from .operations import sync_db, inspect_db
from tabulate import tabulate

from .database import Database
from .configuration import Configuration

click.disable_unicode_literals_warning = True


CONTEXT_SETTINGS = dict(auto_envvar_prefix="dbcut", help_option_names=["-h", "--help"])


class MigrationContext(Context):
    @cached_property
    def dest_db(self):
        return Database(uri=self.config["databases"]["destination_uri"])

    @cached_property
    def src_db(self):
        return Database(uri=self.config["databases"]["source_uri"])


pass_context = make_pass_decorator(MigrationContext)


def load_configuration_file(ctx, param, value):
    if value is not None:
        if os.path.isfile(value) and os.access(value, os.R_OK):
            return Configuration(value)
        else:
            pass


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
def main(ctx, **kwargs):
    """Extract a lightweight subset of your production DB for development and testing purpose."""
    ctx.update_options(**kwargs)
    ctx.configure_log()
    src_uri = ctx.config["databases"]["source_uri"]
    dest_uri = ctx.config["databases"]["destination_uri"]
    ctx.confirm(
        "From -> '%s'\nTo -> '%s'\n\nContinue to extract data ?" % (src_uri, dest_uri),
        default=False,
    )
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
