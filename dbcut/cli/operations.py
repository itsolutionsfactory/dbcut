# -*- coding: utf-8 -*-
from mlalchemy import parse_query
from sqlalchemy.orm import joinedload

from ..utils import to_unicode


def parse_queries(ctx):
    # try a simple YAML-based query first
    queries = []
    session = ctx.src_db.session
    models = ctx.src_db.models
    for dict_query in ctx.config["queries"]:
        dict_query.setdefault("limit", ctx.config["default_limit"])
        query = (
            parse_query(dict_query)
            .to_sqlalchemy(session, models)
            .distinct()
            .options(joinedload("*"))
            .options(cache_key=dict_query)
        )
        queries.append(query)
    return queries


def sync_schema(ctx):
    ctx.src_db.reflect()
    ctx.dest_db.reflect(bind=ctx.src_db.engine)
    ctx.dest_db.drop_all()
    ctx.dest_db.create_all(checkfirst=False)


def copy_query_objects(session, query):
    count, objects = query.with_session(session).load_from_cache()
    if count > 0:
        for item in objects:
            if isinstance(item, dict):
                instance = query.with_session(session).model_class(**item)
            else:
                instance = item
            session.add(instance)
        session.commit()


def sync_data(ctx):
    queries = parse_queries(ctx)
    ctx.dest_db.start_profiler()
    ctx.src_db.start_profiler()

    with ctx.dest_db.no_fkc_session() as session:
        for query in queries:
            if not query.is_cached:
                query.save_to_cache()
            copy_query_objects(session, query)

    ctx.dest_db.stop_profiler()
    ctx.src_db.stop_profiler()
    ctx.dest_db.profiler_stats()
    ctx.src_db.profiler_stats()


def sync_db(ctx):
    sync_schema(ctx)
    sync_data(ctx)


def inspect_db(ctx):
    infos = dict()
    for table_name, size in ctx.src_db.count_all(estimate=True):
        infos[table_name] = {"src_db_size": size, "dest_db_size": 0, "diff": size}
    for table_name, size in ctx.dest_db.count_all():
        if table_name not in infos:
            infos[table_name] = {"src_db_size": 0}
        infos[table_name]["dest_db_size"] = size
        diff = infos[table_name]["src_db_size"] - size
        infos[table_name]["diff"] = diff

    headers = ["Table", "Source estimated size", "Destination size", "Diff"]
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
