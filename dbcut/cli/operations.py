# -*- coding: utf-8 -*-
from mlalchemy import parse_query

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
            .options(cache_key=dict_query)
        )
        queries.append(query)
    return queries


def sync_schema(ctx):
    if not ctx.keep_db:
        ctx.confirm("Remove all tables from %s" % ctx.dest_db.engine.url, default=False)
        ctx.src_db.reflect()
        ctx.dest_db.reflect(bind=ctx.src_db.engine)
        ctx.dest_db.drop_all(checkfirst=True)
        ctx.dest_db.create_all(checkfirst=True)
    else:
        ctx.dest_db.reflect()
        ctx.src_db.reflect(bind=ctx.dest_db.engine)


def sync_data(ctx):

    if ctx.profiler:
        ctx.dest_db.start_profiler()
        ctx.src_db.start_profiler()

    with ctx.dest_db.no_fkc_session() as session:
        for query in parse_queries(ctx):
            if ctx.no_cache:
                objects = query.objects(session)
            else:
                if not query.is_cached or ctx.force_refresh:
                    query.save_to_cache()
                objects = query.load_from_cache(session)
            if objects:
                session.add_all(objects)
                session.commit()
                session.expunge_all()
    if ctx.profiler:
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
    if ctx.sort:
        rows = sorted(rows, key=lambda x: x[0])
    return rows, headers
