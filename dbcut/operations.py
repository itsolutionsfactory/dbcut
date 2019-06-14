# -*- coding: utf-8 -*-
import warnings


from sqlalchemy import create_engine

from .helpers import green


def create_database_if_not_exists(ctx, engine):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        from sqlalchemy_utils.functions import create_database, database_exists
        if not database_exists(engine.url):
            ctx.log(green(' create') + ' ~> new database `%r`' % engine.url)
            create_database(engine.url)
            return True
        return False


def sync_db(ctx):
    from_engine = create_engine(ctx.src_db.engine.url)
    to_engine = create_engine(ctx.dest_db.engine.url)

    # Create database
    create_database_if_not_exists(ctx, to_engine)

    ctx.dest_db.reflect(bind=from_engine)
    ctx.dest_db.drop_all(bind=to_engine, checkfirst=True)
    ctx.dest_db.create_all(bind=to_engine, checkfirst=True)
