# -*- coding: utf-8 -*-
import hashlib
import os
from collections import OrderedDict

from mlalchemy import parse_query as mlalchemy_parse_query
from sqlalchemy.ext import serializer as sa_serializer
from sqlalchemy.orm import (Query, class_mapper, interfaces, joinedload,
                            selectinload)
from sqlalchemy.orm.exc import UnmappedClassError
from sqlalchemy.orm.session import make_transient

from .serializer import to_json
from .utils import merge_dicts, to_unicode


def parse_query(qd, session, config):
    """Parses the given query dictionary to produce a BaseQuery object.
    """
    defaults = {
        "limit": config["default_limit"],
        "backref_depth": config["default_backref_depth"],
        "join_depth": config["default_join_depth"],
        "ignore_tables": [],
    }
    qd.setdefault("limit", defaults["limit"])

    full_qd = merge_dicts(defaults, qd)
    backref_depth = full_qd.get("backref_depth")
    join_depth = full_qd.get("join_depth")
    ignore_tables = full_qd.get("ignore_tables")

    if qd["limit"] in (None, False):
        qd.pop("limit")

    if isinstance(ignore_tables, str):
        ignore_tables = [ignore_tables]

    full_qd["ignore_tables"] = list(set(ignore_tables + config["global_ignore_tables"]))
    query = mlalchemy_parse_query(qd).to_sqlalchemy(session, session.bind._db.models)

    order_by = full_qd.pop("order-by", None)
    if order_by:
        full_qd["order_by"] = order_by

    qd_key_sort = [
        "from",
        "where",
        "order_by",
        "limit",
        "backref_depth",
        "join_depth",
        "ignore_tables",
    ]

    query.query_dict = OrderedDict(
        sorted(full_qd.items(), key=lambda x: qd_key_sort.index(x[0]))
    )
    query = query.with_loaded_relations(
        join_depth, backref_depth, full_qd["ignore_tables"]
    )

    return query


class BaseQuery(Query):

    query_dict = None
    relations_tree = None

    def __init__(self, *args, **kwargs):
        super(BaseQuery, self).__init__(*args, **kwargs)

    class QueryStr(str):
        # Useful for debug
        def __repr__(self):
            return self.replace(" \n", "\n").strip()

    def render(self, reindent=True):
        """Generate an SQL expression string with bound parameters rendered inline
        for the given SQLAlchemy query.
        """
        return self.QueryStr(render_query(self))

    @property
    def cache_key(self):
        if self.query_dict is None:
            raise RuntimeError("Missing 'query_dict'")
        if isinstance(self.query_dict, dict):
            key = to_json(dict(self.query_dict))
        else:
            key = self.query_dict
        return hashlib.sha1(to_unicode(key).encode("utf-8")).hexdigest()

    @property
    def cache_basename(self):
        basename = "{}-{}".format(self.model_class.__name__, self.cache_key)
        return os.path.join(self.session.db.cache_dir, basename)

    @property
    def cache_file(self):
        return "{}.cache".format(self.cache_basename)

    @property
    def count_cache_file(self):
        return "{}.count".format(self.cache_basename)

    @property
    def is_cached(self):
        if self.query_dict is not None:
            return os.path.isfile(self.cache_file)
        return False

    @property
    def model_class(self):
        return self.session.db.models[self._bind_mapper().class_.__name__]

    @property
    def marshmallow_schema(self):
        return self.model_class.__marshmallow__()

    def save_to_cache(self, objects=None):
        if objects is None:
            objects = list(self.objects())
        content = sa_serializer.dumps(objects)
        with open(self.cache_file, "wb") as fd:
            fd.write(content)

    def load_from_cache(self, session=None):
        session = session or self.session
        metadata = session.db.metadata
        with open(self.cache_file, "rb") as fd:
            return sa_serializer.loads(fd.read(), metadata, session)

    def objects(self):
        for obj in self:
            for instance in self.session:
                make_transient(instance)
            yield obj

    def marshmallow_load(self, data, many=True):
        for item in data:
            obj = self.marshmallow_schema.load(item, many=False)
            if isinstance(obj, dict):
                yield self.model_class(**obj)
            else:
                yield obj

    def with_loaded_relations(self, max_join_depth, max_backref_depth, ignore_tables):
        all_models = self.session.db.models
        already_seen_models = [
            all_models.get(table_name)
            for table_name in ignore_tables
            if table_name in all_models
        ]
        relations_to_load = []

        def breadth_first_walk_and_unload_generator(
            root_node,
            model,
            path,
            join_depth=max_join_depth,
            backref_depth=max_backref_depth,
        ):
            already_seen_models.append(model)
            for relationship in get_relationships(model):
                next_path = path + [relationship.key]
                full_path = ".".join(next_path)
                next_models = []
                if relationship.target.name in all_models:
                    target_model = all_models[relationship.target.name]
                    if target_model not in already_seen_models:
                        if (
                            relationship.direction is interfaces.ONETOMANY
                            and backref_depth > 0
                        ):
                            relations_to_load.append((relationship, full_path))
                            next_models.append(
                                (target_model, next_path, relationship.direction)
                            )
                        elif (
                            relationship.direction is interfaces.MANYTOONE
                            and join_depth > 0
                        ):
                            relations_to_load.append((relationship, full_path))
                            next_models.append(
                                (target_model, next_path, relationship.direction)
                            )

                nodes = []
                for next_model, next_path, direction in next_models:
                    next_node = RelationNode(next_model.__name__, root_node)
                    if direction is interfaces.ONETOMANY:
                        gen = breadth_first_walk_and_unload_generator(
                            next_node,
                            next_model,
                            next_path,
                            join_depth,
                            backref_depth - 1,
                        )
                    else:
                        gen = breadth_first_walk_and_unload_generator(
                            next_node,
                            next_model,
                            next_path,
                            join_depth - 1,
                            backref_depth,
                        )
                    nodes.append({"generator": gen, "stop_iteration": False})

                yield

                while not all(node["stop_iteration"] for node in nodes):
                    for node in nodes:
                        if not node["stop_iteration"]:
                            try:
                                yield next(node["generator"])
                            except StopIteration:
                                node["stop_iteration"] = True

        root_node = RelationNode(self.model_class.__name__)
        list(breadth_first_walk_and_unload_generator(root_node, self.model_class, []))

        query = self._clone()
        query.relations_tree = root_node

        for relationship, path in sorted(relations_to_load, key=lambda x: x[1]):
            if relationship.direction is interfaces.ONETOMANY:
                query = query.options(selectinload(path))
            elif relationship.direction is interfaces.MANYTOONE:
                query = query.options(joinedload(path))

        return query


class QueryProperty(object):
    def __init__(self, db):
        self.db = db

    def __get__(self, obj, type):
        try:
            mapper = class_mapper(type)
            if mapper:
                return self.db.query_class(mapper, session=self._db.session)
        except UnmappedClassError:
            return self


def render_query(query, reindent=True):
    """Generate an SQL expression string with bound parameters rendered inline
    for the given SQLAlchemy statement.
    """

    compiled = query.statement.compile(
        dialect=query.session.get_bind().dialect, compile_kwargs={"literal_binds": True}
    )

    raw_sql = str(compiled)
    try:  # pragma: no cover
        import sqlparse

        return sqlparse.format(raw_sql, reindent=reindent)
    except ImportError:  # pragma: no cover
        return raw_sql


class RelationNode:
    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent
        self.children = []

        if parent:
            self.parent.children.append(self)


def get_relationships(model):
    values = model.__mapper__.relationships.values()
    return sorted(values, key=lambda r: (r.direction is interfaces.MANYTOONE, r.key))
