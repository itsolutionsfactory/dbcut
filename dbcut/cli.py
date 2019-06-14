# -*- coding: utf-8 -*-
import click
import os
from .helpers import Context, cached_property, make_pass_decorator
from .operations import sync_db
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
@click.option("-s", "--src-db-url", help="source database url")
@click.option("-d", "--dest-db-url", help="destination database url")
@click.version_option()
@click.option("--verbose", is_flag=True, default=False, help="Enables verbose output.")
@click.option("--debug", is_flag=True, default=False, help="Enables debug mode.")
@pass_context
def main(ctx, **kwargs):
    """Extract a lightweight subset of your production DB for development and testing purpose."""
    ctx.update_options(**kwargs)
    ctx.configure_log()
    ctx.confirm("Continue to migrate your database?", default=True)
    sync_db(ctx)
