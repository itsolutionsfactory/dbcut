# -*- coding: utf-8 -*-
from __future__ import absolute_import

import gzip
import hashlib
import json
import os
import sys
import threading

from sqlalchemy import MetaData, create_engine, event, inspect
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext import serializer as sa_serializer
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.orm import (Query, Session, class_mapper, mapper,
                            scoped_session, sessionmaker)
from sqlalchemy.orm.exc import UnmappedClassError
from sqlalchemy.orm.util import CascadeOptions
from sqlalchemy.schema import conv
from sqlathanor.declarative import BaseModel as SQLAthanorBaseModel

from .compat import reraise, str, to_unicode
from .configuration import DEFAULT_CONFIG
from .helpers import (cached_property, generate_valid_index_name, merge_dicts,
                      to_json)

__all__ = ["Database"]


class DoesNotExist(Exception):
    pass


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

    def save_to_cache_(self):
        content = sa_serializer.dumps(list(self))
        with gzip.open(self.cache_file, "wb") as fd:
            fd.write(content)

    def save_to_cache(self):
        # content = sa_serializer.dumps(list(self))
        # import yaml

        with open(self.cache_file, "wb") as fd:
            # fd.write(to_json(self).encode("utf-8"))
            # __import__("pdb").set_trace()
            fd.write(to_json(self).encode("utf-8"))

    def load_from_cache(self, metadata=None, session=None):
        session = session or self.session
        metadata = metadata or session.db.metadata
        list_dict = []
        with open(self.cache_file, "rb") as fd:
            list_dict = json.loads(fd.read())
        for input_data in list_dict:
            input_data_copy = input_data.copy()
            item = self.model_class.new_from_dict(
                input_data_copy, error_on_extra_keys=True, drop_extra_keys=False
            )
            yield item

    def get_objects(self, metadata=None, session=None):
        for item in self:
            yield self.model_class.new_from_dict(item.to_dict())

    def get_or_error(self, uid):
        """Like :meth:`get` but raises an error if not found instead of
        returning `None`.
        """
        rv = self.get(uid)
        if rv is None:
            raise DoesNotExist()
        return rv

    def first_or_error(self):
        """Like :meth:`first` but raises an error if not found instead of
        returning `None`.
        """
        rv = self.first()
        if rv is None:
            raise DoesNotExist()
        return rv


class BaseSession(Session):
    def __init__(self, db, **options):
        self.db = db
        bind = options.pop("bind", None) or db.engine
        query_cls = options.pop("query_cls", None) or db.query_class
        session_options = merge_dicts(
            dict(autocommit=True, autoflush=True), db._session_options
        )

        Session.__init__(self, bind=bind, query_cls=query_cls, **session_options)


class SessionProperty(object):

    _scoped_sessions = {}

    def __init__(self, db=None):
        self.db = db

    def _create_session_sessionmaker(self, db, options):
        return sessionmaker(class_=BaseSession, db=db, **options)

    def _create_scoped_session(self, db):
        options = db._session_options
        session_factory = self._create_session_sessionmaker(db, options)
        return scoped_session(session_factory)

    def __get__(self, obj, type_):
        if self.db is not None:
            obj = self.db
        if obj is not None:

            if obj not in self._scoped_sessions:
                self._scoped_sessions[obj] = self._create_scoped_session(obj)

            session = self._scoped_sessions[obj]()
            if not obj._reflected:
                obj.reflect(bind=session.bind)

            return session
        return self


class BaseModel(SQLAthanorBaseModel):

    __table_args__ = {"extend_existing": True, "sqlite_autoincrement": True}

    @classmethod
    def create(cls, **kwargs):
        record = cls()
        for key, value in kwargs.items():
            setattr(record, key, value)
        try:
            cls._db.session.add(record)
            cls._db.session.commit()
            return record
        except:
            exc_type, exc_value, tb = sys.exc_info()
            cls._db.session.rollback()
            reraise(exc_type, exc_value, tb.tb_next)

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, inspect(self).identity)


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


class Database(object):
    """This class is used to instantiate a SQLAlchemy connection to
    a database.
    """

    session = SessionProperty()
    session_class = None
    Model = None
    query_class = BaseQuery

    convention = {
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }

    def __init__(self, uri=None, cache_dir=None, session_options=None):
        self.connector = None
        self._reflected = False
        self.cache_dir = cache_dir or DEFAULT_CONFIG["cache"]
        self.uri = uri
        self._session_options = dict(session_options or {})
        self._session_options.setdefault("autoflush", False)
        self._session_options.setdefault("autocommit", False)
        self._engine_lock = threading.Lock()
        self.models = {}
        self.tables = {}
        self.Model = automap_base(
            cls=BaseModel,
            name="Model",
            metadata=MetaData(naming_convention=self.convention),
            metaclass=_BoundDeclarativeMeta,
        )
        self.Model._db = self
        self.Model._query = QueryProperty(self)
        self.Model._session = SessionProperty(self)
        event.listen(mapper, "after_configured", self._configure_serialization)

    @property
    def engine(self):
        """Gives access to the engine. """
        with self._engine_lock:
            if self.connector is None:
                self.connector = EngineConnector(self)
            return self.connector.get_engine()

    @cached_property
    def dialect(self):
        return self.engine.dialect.name

    @property
    def metadata(self):
        """Proxy for Model.metadata"""
        return self.Model.metadata

    @property
    def query(self):
        """Proxy for session.query"""
        return self.session.query

    def add(self, *args, **kwargs):
        """Proxy for session.add"""
        return self.session.add(*args, **kwargs)

    def flush(self, *args, **kwargs):
        """Proxy for session.flush"""
        return self.session.flush(*args, **kwargs)

    def commit(self):
        """Proxy for session.commit"""
        return self.session.commit()

    def rollback(self):
        """Proxy for session.rollback"""
        return self.session.rollback()

    def reflect(self, bind=None):
        """Proxy for Model.prepare"""
        if not self._reflected:
            if bind is None:
                bind = self.engine
            self.Model.prepare(
                bind,
                reflect=True,
                name_for_collection_relationship=self._name_collection_relationship,
            )
            for model in self.models.values():
                for relationship in model.__mapper__.relationships:
                    relationship.cascade = CascadeOptions("all")

            for table in self.tables.values():
                for constraint in table.constraints:
                    if constraint.name:
                        constraint.name = conv(constraint.name)

            if bind.dialect.name == "mysql" and self.dialect != bind.dialect.name:
                self.__fix_indexes__()
            self._reflected = True

    def get_all_indexes(self):
        indexes = []
        for table in self.tables.values():
            for index in table.indexes:
                indexes.append(index)
        return indexes

    def create_all(self, bind=None, **kwargs):
        """Creates all tables. """
        if bind is None:
            bind = self.engine
        self.metadata.create_all(bind=bind, **kwargs)

    def drop_all(self, bind=None, **kwargs):
        """Proxy for metadata.drop_all"""
        if bind is None:
            bind = self.engine
        self.metadata.drop_all(bind=bind, **kwargs)

    def delete_all(self, bind=None, **kwargs):
        """Delete all table content."""
        if bind is None:
            bind = self.engine
        with bind.connect() as con:
            trans = con.begin()
            try:
                for table in reversed(self.metadata.sorted_tables):
                    con.execute(table.delete())
                trans.commit()
            except:
                trans.rollback()
                raise

    def __contains__(self, member):
        return member in self.tables or member in self.models

    def __getitem__(self, name):
        if name in self:
            if name in self.tables:
                return self.tables[name]
            else:
                return self.models[name]
        else:
            raise KeyError(name)

    def close(self, **kwargs):
        """Proxy for Session.close"""
        self.session.close()
        with self._engine_lock:
            if self.connector is not None:
                self.connector.get_engine().dispose()
                self.connector = None

    def show(self):
        """ Return small database content representation."""
        for model_name in sorted(self.models.keys()):
            data = [inspect(i).identity for i in self.models[model_name].query.all()]
            print(model_name.ljust(25), data)

    def __repr__(self):
        engine = None
        if self.connector is not None:
            engine = self.engine
        return "<%s engine=%r>" % (self.__class__.__name__, engine)

    def __fix_indexes__(self):
        for index in self.get_all_indexes():
            index.name = conv(generate_valid_index_name(index, self.engine.dialect))

    def _name_collection_relationship(self, base, local_cls, referred_cls, constraint):
        return referred_cls.__name__.lower() + "_collection"

    def _configure_serialization(self):
        for class_ in self.models.values():
            setattr(class_, "__serialization__", [])
            keynames = set(
                class_.__mapper__.column_attrs.keys()
                + class_.__mapper__.relationships.keys()
            )
            for keyname in keynames:
                support_serialization = True
                if keyname.endswith("_collection"):
                    # exclude serialization
                    support_serialization = False

                class_.set_attribute_serialization_config(
                    keyname,
                    supports_csv=support_serialization,
                    supports_json=support_serialization,
                    supports_yaml=support_serialization,
                    supports_dict=support_serialization,
                )


class EngineConnector(object):
    def __init__(self, db):
        # TODO: parse configuration here
        self._config = {}
        self._db = db
        self._engine = None
        self._connected_for = None
        self._lock = threading.Lock()

    def apply_pool_defaults(self, options):
        def _setdefault(optionkey, configkey):
            value = self._config.get(configkey, None)
            if value is not None:
                options[optionkey] = value

        _setdefault("pool_size", "SQLALCHEMY_POOL_SIZE")
        _setdefault("pool_timeout", "SQLALCHEMY_POOL_TIMEOUT")
        _setdefault("pool_recycle", "SQLALCHEMY_POOL_RECYCLE")
        _setdefault("max_overflow", "SQLALCHEMY_MAX_OVERFLOW")
        _setdefault("convert_unicode", "SQLALCHEMY_CONVERT_UNICODE")

    def apply_driver_hacks(self, info, options):
        """This method is called before engine creation and used to inject
        driver specific hacks into the options.
        """
        if info.drivername == "mysql":
            info.query.setdefault("charset", "utf8")
            options.setdefault("pool_size", 10)
            options.setdefault("pool_recycle", 3600)
            from MySQLdb.cursors import SSCursor as MySQLdb_SSCursor

            if MySQLdb_SSCursor is not None:
                connect_args = options.get("connect_args", {})
                connect_args.update({"cursorclass": MySQLdb_SSCursor})
                options["connect_args"] = connect_args

        elif info.drivername == "sqlite":
            no_pool = options.get("pool_size") == 0
            memory_based = info.database in (None, "", ":memory:")
            if memory_based and no_pool:
                raise ValueError(
                    "SQLite in-memory database with an empty queue"
                    " (pool_size = 0) is not possible due to data loss."
                )
        return options

    def get_engine(self):
        with self._lock:
            uri = self._db.uri
            echo = self._config.get("SQLALCHEMY_ECHO", False)
            if (uri, echo) == self._connected_for:
                return self._engine
            info = make_url(uri)
            options = {}
            self.apply_pool_defaults(options)
            self.apply_driver_hacks(info, options)
            options["echo"] = echo
            self._engine = engine = create_engine(info, **options)
            self._connected_for = (uri, echo)
            return engine


class _BoundDeclarativeMeta(DeclarativeMeta):
    def __new__(cls, name, bases, d):
        from .models import _add_new_class

        d["__module__"] = ".".join(__name__.split(".")[:-1] + ["models"])
        class_ = DeclarativeMeta.__new__(cls, name, bases, d)
        _add_new_class(class_)
        return class_

    def __init__(self, name, bases, d):
        DeclarativeMeta.__init__(self, name, bases, d)
        if hasattr(bases[0], "_db"):
            bases[0]._db.models[name] = self
            bases[0]._db.tables[self.__table__.name] = self.__table__
            self._db = bases[0]._db
