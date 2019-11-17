# -*- coding: utf-8 -*-
import click

from ..context import global_options, pass_context, profiler_option
from ..operations import load
from .cmd_load import load_options


@click.command("dumpjson")
@load_options()
@global_options(default_quiet=True)
@profiler_option()
@pass_context
def cli(ctx, **kwargs):
    """Export data to json."""
    ctx.export_json = True
    load(ctx)
