# -*- coding: utf-8 -*-

import click

from ..context import global_options, pass_context, profiler_option
from ..operations import inspect_db


@click.command("inspect")
@profiler_option()
@click.option(
    "--estimate",
    "--no-estimate",
    is_flag=True,
    default=True,
    help="Disables estimation and perform a real count().",
)
@global_options()
@pass_context
def cli(ctx, **kwargs):
    """Check databases content."""
    inspect_db(ctx)
