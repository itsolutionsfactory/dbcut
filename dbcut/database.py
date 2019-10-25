# -*- coding: utf-8 -*-
from __future__ import absolute_import

import re
import sys
import threading
from contextlib import contextmanager

from marshmallow import fields, post_dump
from marshmallow_sqlalchemy import ModelSchema
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.automap import automap_base, generate_relationship
from sqlalchemy.orm import mapper
from sqlalchemy.schema import conv

from .configuration import DEFAULT_CONFIG
from .marshmallow_schema import register_new_schema
from .models import BaseDeclarativeMeta, BaseModel
from .query import BaseQuery, QueryProperty
from .session import SessionProperty
from .utils import cached_property, generate_valid_index_name, to_unicode

try:
    from easy_profile import SessionProfiler, StreamReporter
except ImportError:
    from .utils import VoidObject

    SessionProfiler = StreamReporter = VoidObject


__all__ = ["Database"]


class Database(object):
    """This class is used to instantiate a SQLAlchemy connection to
    a database.
    """

    session = SessionProperty()
    query_class = BaseQuery

    def __init__(
        self,
        uri=None,
        cache_dir=None,
        session_options=None,
        echo_sql=False,
        echo_stream=None,
    ):
        self.connector = None
        self._reflected = False
        self.echo_sql = echo_sql
        self.echo_stream = echo_stream or sys.stdout
        self.cache_dir = cache_dir or DEFAULT_CONFIG["cache"]
        self.uri = uri
        self._session_options = dict(session_options or {})
        self._session_options.setdefault("autoflush", False)
        self._session_options.setdefault("autocommit", False)
        self._engine_lock = threading.Lock()
        self._model_class_registry = {}
        self.profiler = SessionProfiler(engine=self.engine)

        self.Model = automap_base(
            cls=type("BaseModel", (BaseModel,), {}),
            name="Model",
            metaclass=BaseDeclarativeMeta,
        )
        self.Model._db = self
        self.Model._session = SessionProperty(self)
        self.Model._query = QueryProperty(self)

        event.listen(self.engine, "before_cursor_execute", self._before_custor_execute)
        event.listen(self.engine, "after_cursor_execute", self._after_custor_execute)
        event.listen(mapper, "after_configured", self._configure_serialization)

    def start_profiler(self):
        self.profiler.begin()

    def stop_profiler(self):
        self.profiler.commit()

    def profiler_stats(self):
        StreamReporter(file=sys.stderr).report(self.engine, self.profiler.stats)

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
                bind, reflect=True, generate_relationship=self._gen_relationship
            )

            for table in self.tables.values():
                for constraint in table.constraints:
                    if constraint.name:
                        constraint.name = conv(constraint.name)

            for index in self.get_all_indexes():
                index.name = conv(generate_valid_index_name(index, self.engine.dialect))

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

    def drop_all(self, checkfirst=True):
        """Proxy for metadata.drop_all"""
        with self.no_fkc_session() as session:
            self.metadata.drop_all(session.bind, checkfirst=checkfirst)

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

    def close(self, **kwargs):
        """Proxy for Session.close"""
        self.session.close()
        with self._engine_lock:
            if self.connector is not None:
                self.connector.get_engine().dispose()
                self.connector = None

    @property
    def models(self):
        return self._model_class_registry

    @property
    def tables(self):
        return self.metadata.tables

    @contextmanager
    def no_fkc_session(self):
        """ A context manager that give a session with all foreign key constraints disabled. """
        scoped_session = self.session
        try:
            scoped_session.remove()
            session = scoped_session()
            if session.bind.dialect.name == "mysql":
                session.execute("SET FOREIGN_KEY_CHECKS = 0")
            elif session.bind.dialect.name == "sqlite":
                session.execute("PRAGMA foreign_keys = OFF")
            elif session.bind.dialect.name == "postgresql":
                for table_name in self.tables:
                    session.execute(
                        "ALTER TABLE IF EXISTS %s DISABLE TRIGGER ALL" % table_name
                    )

            yield session

            if session.bind.dialect.name == "mysql":
                session.execute("SET FOREIGN_KEY_CHECKS = 1")
            elif session.bind.dialect.name == "sqlite":
                session.execute("PRAGMA foreign_keys = ON")
            elif session.bind.dialect.name == "postgresql":
                for table_name in self.tables:
                    session.execute(
                        "ALTER TABLE IF EXISTS %s ENABLE TRIGGER ALL" % table_name
                    )

            session.close()
        finally:
            session.close()
            scoped_session.remove()

    def show(self):
        """ Return small database content representation."""
        for model_name in sorted(self.models.keys()):
            data = [inspect(i).identity for i in self.models[model_name].query.all()]
            print(model_name.ljust(25), data)

    def _gen_relationship(
        self, base, direction, return_fn, attrname, local_cls, referred_cls, **kw
    ):
        kw["lazy"] = "noload"
        kw["cascade"] = "all"
        return generate_relationship(
            base, direction, return_fn, attrname, local_cls, referred_cls, **kw
        )

    def _configure_serialization(self):
        module_basename = ".".join(
            self.__class__.__module__.split(".")[:-1] + ["marshmallow_schema"]
        )

        for class_ in self.models.values():

            class Meta(object):
                model = class_
                transient = True
                include_fk = True

            attrs = {"Meta": Meta}
            attrs["__module__"] = module_basename
            schema_class_name = "%s_%s_marshmallow_schema" % (id(self), class_.__name__)

            relationship_keys = class_.__mapper__.relationships.keys()

            for keyname in relationship_keys:
                relationship = class_.__mapper__.relationships[keyname]
                target_name = relationship.target.name
                if target_name in self.models:

                    many = relationship.uselist

                    target_schema_class_name = "%s_%s_marshmallow_schema" % (
                        id(self),
                        self.models[target_name].__name__,
                    )
                    target_schema_class_fullname = "%s.%s" % (
                        attrs["__module__"],
                        target_schema_class_name,
                    )
                    exclude_keys = []

                    if target_name == class_.__name__:
                        exclude_keys = [keyname]
                        attrs[keyname] = fields.Nested(
                            "self",
                            name=keyname,
                            many=many,
                            exclude=exclude_keys,
                            default=None,
                        )
                    else:
                        attrs[keyname] = fields.Nested(
                            target_schema_class_fullname,
                            name=keyname,
                            many=many,
                            exclude=exclude_keys,
                        )

            schema_class = type(schema_class_name, (BaseSchema,), attrs)
            register_new_schema(schema_class)
            setattr(class_, "__marshmallow__", schema_class)

        for class_ in self.models.values():
            for key, field in class_.__marshmallow__._declared_fields.items():
                if field:
                    field.allow_none = True

    def _echo_statement(self, stm):
        text = to_unicode(stm)
        text = re.sub(r";", ";\n", text)
        text = re.sub(r"\n+", "\n", text).strip()
        if text.startswith(("CREATE TABLE", "BEGIN")):
            self.echo_stream.write("\n")

        self.echo_stream.write(text)
        self.echo_stream.write(";\n")
        self.echo_stream.flush()

    def _before_custor_execute(
        self, conn, cursor, statement, parameters, context, executemany
    ):
        if self.echo_sql:
            if conn.engine.dialect.name == "sqlite":
                conn.connection.connection.set_trace_callback(
                    lambda x: self._echo_statement(x)
                )

    def _after_custor_execute(
        self, conn, cursor, statement, parameters, context, executemany
    ):
        if self.echo_sql:
            if conn.engine.dialect.name == "mysql":
                self._echo_statement(cursor._last_executed)
            if conn.engine.dialect.name == "postgresql":
                self._echo_statement(cursor.query)

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

    def __repr__(self):
        engine = None
        if self.connector is not None:
            engine = self.engine
        return "<%s engine=%r>" % (self.__class__.__name__, engine)


class BaseSchema(ModelSchema):
    SKIP_VALUES = set([None])

    @post_dump
    def remove_skip_values(self, data, **kwargs):
        return dict(
            (
                (key, value)
                for key, value in data.items()
                if value is not None or not isinstance(self.fields[key], fields.Nested)
            )
        )


class EngineConnector(object):
    def __init__(self, db, connect_timeout=3):
        self._db = db
        self._engine = None
        self.connect_timeout = connect_timeout
        self._lock = threading.Lock()

    def get_engine(self):
        with self._lock:
            if self._engine is None:
                options = {}
                info = make_url(self._db.uri)
                if info.drivername in ("mysql", "postgresql"):
                    connect_args = dict(info.query)
                    connect_args["connect_timeout"] = int(
                        connect_args.get("connect_timeout", self.connect_timeout)
                    )
                    options["connect_args"] = connect_args
                    if info.drivername == "mysql":
                        info.query.setdefault("charset", "utf8")
                        options.setdefault("pool_size", 10)
                        options.setdefault("pool_recycle", 3600)

                        try:
                            from MySQLdb.cursors import SSCursor

                            connect_args.update({"cursorclass": SSCursor})
                        except ImportError:
                            pass

                    elif info.drivername == "postgresql":
                        options.setdefault("use_batch_mode", True)

                elif info.drivername == "sqlite":
                    no_pool = options.get("pool_size") == 0
                    memory_based = info.database in (None, "", ":memory:")
                    if memory_based and no_pool:
                        raise ValueError(
                            "SQLite in-memory database with an empty queue"
                            " (pool_size = 0) is not possible due to data loss."
                        )

                self._engine = create_engine(info, **options)
                self._engine._db = self._db
            return self._engine
