# -*- coding: utf-8 -*-
import warnings

from mlalchemy import parse_query
from sqlalchemy import MetaData, Table, func
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import select

from ..compat import to_unicode

# Disable pymysql warning
try:
    import pymysql

    warnings.filterwarnings("ignore", category=pymysql.Warning)
except ImportError:
    pass


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
        # dict_query.setdefault("limit", 100)
        query = (
            parse_query(dict_query)
            .to_sqlalchemy(session, models)
            .distinct()
            .options(joinedload("*"))
        )
        queries.append(query)
    return queries


def sync_schema(ctx):
    ctx.src_db.reflect()
    ctx.dest_db.reflect(bind=ctx.src_db.engine)
    ctx.dest_db.drop_all()
    ctx.dest_db.create_all(checkfirst=False)


def copy_query_objects(ctx, query):
    scoped = ctx.dest_db.session
    try:
        scoped.remove()
        session = scoped()
        count, objects = query.with_session(session).load_from_cache()
        if count > 0:
            for item in objects:
                if isinstance(item, dict):
                    instance = query.with_session(session).model_class(**item)
                else:
                    instance = item
                session.add(instance)
            session.commit()
        session.close()
    finally:
        session.close()
        scoped.remove()


def sync_data(ctx):
    queries = parse_queries(ctx)
    ctx.dest_db.start_profiler()
    ctx.src_db.start_profiler()
    for query in queries:
        query.save_to_cache()
        copy_query_objects(ctx, query)

    ctx.dest_db.stop_profiler()
    ctx.src_db.stop_profiler()
    ctx.dest_db.profiler_stats()
    ctx.src_db.profiler_stats()


def sync_db(ctx):
    sync_schema(ctx)
    sync_data(ctx)


def inspect_db(ctx):
    infos = dict()
    for table_name, size in count_all(ctx.src_db.engine):
        infos[table_name] = {"src_db_size": size, "dest_db_size": 0, "diff": size}
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
