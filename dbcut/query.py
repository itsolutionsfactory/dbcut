# -*- coding: utf-8 -*-
import hashlib
import os

from sqlalchemy.orm import Query, class_mapper, subqueryload
from sqlalchemy.orm.exc import UnmappedClassError

from .serializer import dump_json, load_json, to_json
from .utils import aslist, get_all_onetomany_keys, to_unicode


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
        load_backrefs = kwargs.get("load_backrefs", None)
        if cache_key:
            query = query._clone()
            if isinstance(cache_key, dict):
                cache_key = to_json(cache_key)
            query.cache_key = hashlib.sha1(
                to_unicode(cache_key).encode("utf-8")
            ).hexdigest()

        if load_backrefs:
            query = query._clone()
            backref_keys = get_all_onetomany_keys(self.model_class)
            load = None
            if backref_keys:
                load = subqueryload(backref_keys[0])
                for key in backref_keys[1:]:
                    load = subqueryload(key)
                query = query._options(False, load)

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
        data = self.marshmallow_schema.dump(self, many=True).data
        dump_json(data, self.cache_file)

    def load_from_cache(self, session):
        session = session or self.session
        data = load_json(self.cache_file)
        return self.with_session(session).marshmallow_load(data, many=True)

    @aslist
    def objects(self, session=None):
        session = session or self.session
        data = self.marshmallow_schema.dump(self, many=True).data
        return self.with_session(session).marshmallow_load(data, many=True)

    @aslist
    def marshmallow_load(self, data, many=True):
        for obj in self.marshmallow_schema.load(data, many=True).data:
            if isinstance(obj, dict):
                yield self.model_class(**obj)
            else:
                yield obj


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
