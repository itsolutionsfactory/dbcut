# -*- coding: utf-8 -*-
import hashlib
import os

from sqlalchemy.orm import (Query, class_mapper, interfaces, joinedload,
                            noload, subqueryload)
from sqlalchemy.orm.exc import UnmappedClassError

from .serializer import dump_json, load_json, to_json
from .utils import aslist, to_unicode


class BaseQuery(Query):

    cache_key = None

    class QueryStr(str):
        # Useful for debug
        def __repr__(self):
            return self.replace(" \n", "\n").strip()

    def render(self, reindent=True):
        """Generate an SQL expression string with bound parameters rendered inline
        for the given SQLAlchemy query.
        """
        return self.QueryStr(render_query(self))

    def options(self, *args, **kwargs):
        query = self
        cache_key = kwargs.get("cache_key", None)
        prevent_loop = kwargs.get("prevent_loop", None)
        if cache_key:
            query = query._clone()
            if isinstance(cache_key, dict):
                cache_key = to_json(cache_key)
            query.cache_key = hashlib.sha1(
                to_unicode(cache_key).encode("utf-8")
            ).hexdigest()

        if prevent_loop:
            query = self._prevent_loop_loading()

        if args:
            return query._options(False, *args)
        else:
            return query

    @property
    def cache_file(self):
        if self.cache_key is None:
            raise RuntimeError("Missing 'cache_key'")
        filename = "%s-%s.json" % (self.model_class.__name__, self.cache_key)
        return os.path.join(self.session.db.cache_dir, filename)

    @property
    def is_cached(self):
        if self.cache_key is not None:
            return os.path.isfile(self.cache_file)
        return False

    @property
    def model_class(self):
        return self.session.db.models[self._bind_mapper().class_.__name__]

    @property
    def marshmallow_schema(self):
        return self.model_class.__marshmallow__()

    def save_to_cache(self):
        data = self.marshmallow_schema.dump(self, many=True)
        dump_json(data, self.cache_file)

    def load_from_cache(self, session):
        session = session or self.session
        data = load_json(self.cache_file)
        return self.with_session(session).marshmallow_load(data, many=True)

    @aslist
    def objects(self, session=None):
        session = session or self.session
        data = self.marshmallow_schema.dump(self, many=True)
        return self.with_session(session).marshmallow_load(data, many=True)

    @aslist
    def marshmallow_load(self, data, many=True):
        for obj in self.marshmallow_schema.load(data, many=True):
            if isinstance(obj, dict):
                yield self.model_class(**obj)
            else:
                yield obj

    def _prevent_loop_loading(self):
        all_models = self.session.db.models
        already_seen_models = []
        relations_to_noload = []

        def walk_tree_and_unload(model, path):
            if model not in already_seen_models:
                already_seen_models.append(model)
                for relationship in model.__mapper__.relationships.values():
                    next_path = path + [relationship.key]
                    full_path = ".".join(next_path)
                    if relationship.target.name in all_models:
                        target_model = all_models[relationship.target.name]
                        if target_model in already_seen_models:
                            relations_to_noload.append((relationship, full_path))
                        else:
                            walk_tree_and_unload(target_model, next_path)

        walk_tree_and_unload(self.model_class, [])
        query = self._clone()

        for relationship, path in relations_to_noload:
            query = query.options(noload(path))

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
