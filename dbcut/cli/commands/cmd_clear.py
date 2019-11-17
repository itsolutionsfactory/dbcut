# -*- coding: utf-8 -*-

import click

from ..context import global_options, pass_context, profiler_option
from ..operations import clear


@click.command("clear")
@profiler_option()
@global_options()
@pass_context
def cli(ctx, **kwargs):
    """Remove all data (only) from the target database"""
    clear(ctx)
