# -*- coding: utf-8 -*-
import os
from contextlib import contextmanager
from itertools import chain

from sqlalchemy_utils.functions import create_database, database_exists, drop_database
from tabulate import tabulate
from tqdm import tqdm

from ..parser import parse_query
from ..serializer import dump_yaml
from ..utils import get_directory_size, to_unicode


def parse_queries(ctx):
    queries = []
    session = ctx.src_db.session
    if ctx.only_tables:
        raw_queries = [q for q in ctx.config["queries"] if q["from"] in ctx.only_tables]
    else:
        raw_queries = ctx.config["queries"]

    if ctx.last_only and raw_queries:
        raw_queries = [raw_queries[-1]]

    for dict_query in raw_queries:
        queries.append(parse_query(dict_query.copy(), session, ctx.config))
    return queries


@contextmanager
def db_profiling(ctx):
    if ctx.profiler:
        ctx.src_db.start_profiler()
        ctx.dest_db.start_profiler()
    yield
    if ctx.profiler:
        ctx.src_db.stop_profiler()
        ctx.dest_db.stop_profiler()
        ctx.src_db.profiler_stats()
        ctx.dest_db.profiler_stats()


def get_objects_generator(ctx, query, session):

    if ctx.no_cache or ctx.force_refresh or not query.is_cached:
        using_cache = False
        count = query.count()
        generator = query.objects()
    else:
        using_cache = True
        count, data = query.load_from_cache(session=session)
        generator = (obj for obj in data)

    def objects_generator():
        progressbar = None

        obj = next(generator, None)
        if obj is not None:
            fetch_generator = chain([obj], generator)
        else:
            fetch_generator = generator

        yield

        if not using_cache:
            progressbar = tqdm(total=count, leave=False)

        for obj in fetch_generator:
            yield obj
            if progressbar is not None:
                progressbar.update(1)

        if progressbar is not None:
            progressbar.close()

    return objects_generator(), count, using_cache


def save_query_cache(ctx, query, objects):
    if ctx.no_cache:
        return
    if ctx.force_refresh or not query.is_cached:
        query.save_to_cache(objects=objects)


def copy_query(ctx, query, session, query_index, number_of_queries):
    objects_generator, count, using_cache = get_objects_generator(ctx, query, session)

    ctx.log("")
    ctx.log("Query %d/%d : " % ((query_index + 1), number_of_queries), nl=False)
    ctx.log("")
    ctx.log("")
    ctx.log(dump_yaml(query.query_dict), prefix="    ")
    ctx.log("", quietable=True)
    ctx.log(
        query.relation_tree.render(return_value=True), tty_truncate=True, quietable=True
    )
    ctx.log(" ---> Cache key : %s" % query.cache_key, quietable=True)

    continue_operation = True
    if ctx.interactive:
        continue_operation = ctx.continue_operation("Continue ?", default=False)

    if continue_operation:
        if using_cache:
            ctx.log(" ---> Using cache ({} elements)".format(count), quietable=True)
        else:
            ctx.log(" ---> Executing query")

        next(objects_generator)

        if count:
            ctx.log(" ---> Fetching objects")
            objects_to_serialize = list(objects_generator)
            save_query_cache(ctx, query, objects_to_serialize)

            if ctx.export_json:
                ctx.log(" ---> Exporting json to {}".format(query.json_file))
                query.export_to_json(objects_to_serialize)
            else:
                session.add_all(objects_to_serialize)
                ctx.log(" ---> Inserting {} rows".format(len(list(session))))
                session.commit()

        else:
            ctx.log(" ---> Nothing to do")
    else:
        ctx.log(" ---> Skipped")


def load_data(ctx):
    with db_profiling(ctx):
        with ctx.dest_db.no_fkc_session() as session:
            queries = parse_queries(ctx)
            number_of_queries = len(queries)
            for query_index, query in enumerate(queries):
                copy_query(ctx, query, session, query_index, number_of_queries)


def sync_schema(ctx):
    ctx.log(" ---> Reflecting database schema from %s" % repr(ctx.src_db_uri))
    ctx.src_db.reflect()
    if not database_exists(ctx.dest_db_uri):
        create_db(ctx)
    create_tables(ctx)


def create_db(ctx):
    if not database_exists(ctx.dest_db_uri):
        ctx.log(" ---> Creating new %s database" % repr(ctx.dest_db_uri))
        create_database(ctx.dest_db_uri)


def create_tables(ctx, checkfirst=True):
    ctx.dest_db.prepare()
    ctx.log(" ---> Creating all tables and relations on %s" % repr(ctx.dest_db_uri))
    ctx.dest_db.create_all(checkfirst=checkfirst)


def flush(ctx):
    if ctx.with_cache:
        purge_cache(ctx)
    if database_exists(ctx.dest_db_uri):
        ctx.confirm("Removes ALL TABLES from %s" % repr(ctx.dest_db_uri), default=False)
        ctx.log(" ---> Removing %s database" % repr(ctx.dest_db_uri))
        drop_database(ctx.dest_db_uri)
    create_db(ctx)
    ctx.log(" ---> Reflecting database schema from %s" % repr(ctx.src_db_uri))
    ctx.src_db.reflect()
    create_tables(ctx, checkfirst=False)


def clear(ctx):
    if database_exists(ctx.dest_db_uri):
        ctx.confirm("Removes ALL data from %s" % repr(ctx.dest_db_uri), default=False)
        ctx.log(
            " ---> Removing all data from {} database".format(repr(ctx.dest_db_uri))
        )
        ctx.dest_db.delete_all()


def load(ctx):
    sync_schema(ctx)
    load_data(ctx)


def inspect_db(ctx):
    infos = dict()
    for table_name, size in ctx.src_db.count_all(estimate=ctx.estimate):
        infos[table_name] = {"src_db_size": size, "dest_db_size": 0, "diff": size}
    for table_name, size in ctx.dest_db.count_all():
        if table_name not in infos:
            infos[table_name] = {"src_db_size": 0}
        infos[table_name]["dest_db_size"] = size
        diff = infos[table_name]["src_db_size"] - size
        infos[table_name]["diff"] = diff

    if ctx.estimate:
        headers = ["Table", "Source estimated size", "Destination size", "Diff"]
    else:
        headers = ["Table", "Source size", "Destination size", "Diff"]

    rows = [
        (
            k,
            to_unicode(infos[k]["src_db_size"]),
            to_unicode(infos[k]["dest_db_size"]),
            to_unicode(infos[k]["diff"]),
        )
        for k in infos.keys()
    ]
    rows = sorted(rows, key=lambda x: x[0])

    ctx.log(" ---> Databases ")
    ctx.log("")
    ctx.log(tabulate(rows, headers=headers), prefix="    ")
    ctx.log("")
    ctx.log("")
    ctx.log(" ---> Cache ")
    ctx.log("")
    ctx.log("location : %s" % ctx.config["cache"], prefix="    ")
    ctx.log(
        "Disk usage : %.1f MB" % get_directory_size(ctx.config["cache"]), prefix="    "
    )
    ctx.log("")


def purge_cache(ctx):
    included_extensions = ["cache", "count"]

    def listfiles(path):
        for r, d, f in os.walk(path):
            for file in f:
                yield os.path.join(r, file)

    file_names = [
        fn
        for fn in listfiles(ctx.config["cache"])
        if any(fn.endswith(ext) for ext in included_extensions)
    ]

    for file in file_names:
        os.remove(file)
    ctx.log(" ---> Purged all cache")
