# -*- coding: utf-8 -*-

import click

from ..context import global_options, pass_context, profiler_option
from ..operations import flush, purge_cache


@click.command("flush")
@profiler_option()
@click.option(
    "--with-cache", is_flag=True, default=False, help="Also delete all cache",
)
@global_options()
@pass_context
def cli(ctx, **kwargs):
    """Remove ALL TABLES from the target database and recreate them"""
    flush(ctx)
