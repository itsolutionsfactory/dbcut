# -*- coding: utf-8 -*-

import click

from ..context import global_options, pass_context, profiler_option
from ..operations import flush, purge_cache


@click.command("flush")
@profiler_option()
@global_options()
@pass_context
def cli(ctx, **kwargs):
    """Purge cache, remove ALL TABLES from the target database and recreate them"""
    purge_cache(ctx)
    flush(ctx)
