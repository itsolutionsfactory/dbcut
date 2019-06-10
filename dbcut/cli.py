# -*- coding: utf-8 -*-
import click

from .helpers import (Context, cached_property, make_pass_decorator)
from .operations import sync_db
from .database import Database

click.disable_unicode_literals_warning = True


CONTEXT_SETTINGS = dict(auto_envvar_prefix='dbcut',
                        help_option_names=['-h', '--help'])


class MigrationContext(Context):

    @cached_property
    def new_db(self):
        return Database(uri=self.new_db_url)

    @cached_property
    def current_db(self):
        return Database(uri=self.current_db_url)

    @cached_property
    def new_db_name(self):
        return self.new_db.engine.url.database

    @cached_property
    def current_db_name(self):
        return self.current_db.engine.url.database

    @cached_property
    def current_tables(self):
        """ Return a namespace with all tables classes"""
        self.current_db.reflect()
        sorted_tables = self.current_db.metadata.sorted_tables
        return dict((t.name, t) for t in sorted_tables)


pass_context = make_pass_decorator(MigrationContext)


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--schema-only', is_flag=True, default=False,
              help="Migrates only the schema, no data")
@click.option('--current-db-url', help='the url for your current database.')
@click.option('--new-db-url', help='the url for your new database.')
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
