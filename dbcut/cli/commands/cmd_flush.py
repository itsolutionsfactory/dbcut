# -*- coding: utf-8 -*-

import click

from ..context import global_options, pass_context, profiler_option
from ..operations import flush


@click.command("flush")
@profiler_option()
@global_options()
@pass_context
def cli(ctx, **kwargs):
    """Removes ALL TABLES from the target database and recreates them"""
    flush(ctx)