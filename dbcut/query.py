# -*- coding: utf-8 -*-
import hashlib
import os

from io import open
from sqlalchemy.orm import Query, class_mapper
from sqlalchemy.orm.exc import UnmappedClassError

from .compat import str, to_json, to_unicode


class BaseQuery(Query):
    class QueryStr(str):
        # Useful for debug
        def __repr__(self):
            return self.replace(" \n", "\n").strip()

    def render(self, reindent=True):
        """Generate an SQL expression string with bound parameters rendered inline
        for the given SQLAlchemy query.
        """

        statement = self.with_labels().statement
        raw_sql = to_unicode(statement.compile(compile_kwargs={"literal_binds": True}))

        try:  # pragma: no cover
            import sqlparse

            raw_sql = sqlparse.format(raw_sql, reindent=reindent)
        except ImportError:  # pragma: no cover
            return raw_sql

        return self.QueryStr(raw_sql)

    @property
    def cache_key(self):
        sha1_hash = hashlib.sha1(self.render().encode("utf-8")).hexdigest()
        return "%s-%s" % (self.model_class.__name__, sha1_hash)

    @property
    def cache_file(self):
        return "%s.json" % os.path.join(self.session.db.cache_dir, self.cache_key)

    @property
    def is_cached(self):
        return os.path.isfile(self.cache_file)

    @property
    def model_class(self):
        return self.session.db.models[self._bind_mapper().class_.__name__]

    @property
    def marshmallow_schema(self):
        return self.model_class.__marshmallow__()

    def save_to_cache(self):
        dict_dump = self.marshmallow_schema.dump(list(self), many=True).data
        with open(self.cache_file, "w", encoding="utf-8") as fd:
            jsontext = to_json(dict_dump)
            fd.write(to_unicode(jsontext))

    def load_from_cache(self):
        with open(self.cache_file, "r", encoding="utf-8") as fd:
            return self.marshmallow_schema.loads(fd.read(), many=True).data


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
