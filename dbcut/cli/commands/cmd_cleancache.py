# -*- coding: utf-8 -*-

import click

from ..context import global_options, pass_context, profiler_option
from ..operations import clean_cache


@click.command("cleancache")
@profiler_option()
@global_options()
@pass_context
def cli(ctx, **kwargs):
    """ Remove all cached queries."""
    clean_cache(ctx)
