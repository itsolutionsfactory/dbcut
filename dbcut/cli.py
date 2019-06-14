# -*- coding: utf-8 -*-
import click

from .helpers import (Context, cached_property, make_pass_decorator)
from .operations import sync_db
from .database import Database

click.disable_unicode_literals_warning = True


CONTEXT_SETTINGS = dict(auto_envvar_prefix='dbcut', help_option_names=['-h', '--help'])


class MigrationContext(Context):

    @cached_property
    def dest_db(self):
        return Database(uri=self.dest_db_url)

    @cached_property
    def src_db(self):
        return Database(uri=self.src_db_url)


pass_context = make_pass_decorator(MigrationContext)


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--schema-only', is_flag=True, default=False,
              help="Migrates only the schema, no data")
@click.option('-s', '--src-db-url', help='source database url')
@click.option('-d', '--dest-db-url', help='destination database url')
@click.option('--chunk', type=int, default=100000, show_default=True,
              help="Defines the chunk size")
@click.option('-y', '--force-yes', is_flag=True, default=False,
              help="Never prompts for user intervention")
@click.version_option()
@click.option('--verbose', is_flag=True, default=False,
              help="Enables verbose output.")
@click.option('--debug', is_flag=True, default=False,
              help="Enables debug mode.")
@pass_context
def main(ctx, **kwargs):
    """Extract a lightweight subset of your production DB for development and testing purpose."""
    ctx.update_options(**kwargs)
    ctx.configure_log()
    ctx.confirm("Continue to migrate your database?", default=True)
    sync_db(ctx)
