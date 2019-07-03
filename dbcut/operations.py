# -*- coding: utf-8 -*-
import warnings

from mlalchemy import parse_query
from sqlalchemy import MetaData, Table, create_engine, func
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import select

from .compat import to_unicode
from .helpers import green


def database_exists(*args, **kwargs):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        from sqlalchemy_utils.functions import database_exists

        return database_exists(*args, **kwargs)


def create_database(*args, **kwargs):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        from sqlalchemy_utils.functions import create_database

        return create_database(*args, **kwargs)


def create_database_if_not_exists(ctx, engine):
    if not database_exists(engine.url):
        ctx.log(green(" create") + " ~> new database `%r`" % engine.url)
        create_database(engine.url)
        return True
    return False


def reflect_table(engine, table_name):
    metadata = MetaData(engine)
    return Table(table_name, metadata, autoload=True)


def count_all(engine):
    raw_conn = engine.connect()
    inspector = Inspector.from_engine(engine)
    tables = [reflect_table(engine, name) for name in inspector.get_table_names()]
    for table in tables:
        count_query = select([func.count()]).select_from(table)
        yield table.name, raw_conn.execute(count_query).scalar()


def parse_queries(ctx):
    # try a simple YAML-based query first
    queries = []
    session = ctx.src_db.session
    models = ctx.src_db.models
    for dict_query in ctx.config["queries"]:
        dict_query.setdefault("limit", 100)
        query = (
            parse_query(dict_query)
            .to_sqlalchemy(session, models)
            .distinct()
            .options(joinedload("*"))
        )
        queries.append(query)
    return queries


def sync_schema(ctx):
    from_engine = create_engine(ctx.src_db.engine.url)
    to_engine = create_engine(ctx.dest_db.engine.url)

    # Create database
    create_database_if_not_exists(ctx, to_engine)

    ctx.dest_db.reflect(bind=from_engine)
    ctx.dest_db.drop_all(bind=to_engine, checkfirst=True)
    ctx.dest_db.create_all(bind=to_engine, checkfirst=True)


def sync_data(ctx):
    queries = parse_queries(ctx)
    dest_session = ctx.dest_db.session
    src_session = ctx.src_db.session
    dest_session.execute("SET FOREIGN_KEY_CHECKS = 0;")
    for query in queries:
        src_query = query.with_session(src_session)
        query.with_session(dest_session).merge_result(src_query)


def sync_db(ctx):
    sync_schema(ctx)
    sync_data(ctx)


def inspect_db(ctx):
    infos = dict()
    for table_name, size in count_all(ctx.src_db.engine):
        infos[table_name] = {"src_db_size": size, "dest_db_size": 0, "diff": size}
    if database_exists(ctx.dest_db.engine.url):
        for table_name, size in count_all(ctx.dest_db.engine):
            infos[table_name]["dest_db_size"] = size
            diff = infos[table_name]["src_db_size"] - size
            infos[table_name]["diff"] = diff

    headers = ["Table", "Source DB count", "Destination DB count", "Diff"]
    rows = [
        (
            k,
            to_unicode(infos[k]["src_db_size"]),
            to_unicode(infos[k]["dest_db_size"]),
            to_unicode(infos[k]["diff"]),
        )
        for k in infos.keys()
    ]
    return sorted(rows, key=lambda x: x[0]), headers
