# -*- coding: utf-8 -*-
# This module comes from the sqlalchemy-utils package
# These functions have been slightly patched to support sqlalchemy 1.4+
import os
from copy import copy

import sqlalchemy as sa
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm.exc import UnmappedInstanceError
from sqlalchemy.orm.session import object_session
from sqlalchemy.pool import NullPool


def get_bind(obj):
    """
    Return the bind for given SQLAlchemy Engine / Connection / declarative
    model object.
    :param obj: SQLAlchemy Engine / Connection / declarative model object
    ::
        from sqlalchemy_utils import get_bind
        get_bind(session)  # Connection object
        get_bind(user)
    """
    if hasattr(obj, "bind"):
        conn = obj.bind
    else:
        try:
            conn = object_session(obj).bind
        except UnmappedInstanceError:
            conn = obj

    if not hasattr(conn, "execute"):
        raise TypeError(
            "This method accepts only Session, Engine, Connection and "
            "declarative model objects."
        )
    return conn


def quote(mixed, ident):
    """
    Conditionally quote an identifier.
    ::
        from sqlalchemy_utils import quote
        engine = create_engine('sqlite:///:memory:')
        quote(engine, 'order')
        # '"order"'
        quote(engine, 'some_other_identifier')
        # 'some_other_identifier'
    :param mixed: SQLAlchemy Session / Connection / Engine / Dialect object.
    :param ident: identifier to conditionally quote
    """
    if isinstance(mixed, Dialect):
        dialect = mixed
    else:
        dialect = get_bind(mixed).dialect
    return dialect.preparer(dialect).quote(ident)


def database_exists(url):
    """Check if a database exists.
    :param url: A SQLAlchemy engine URL.
    Performs backend-specific testing to quickly determine if a database
    exists on the server. ::
        database_exists('postgresql://postgres@localhost/name')  #=> False
        create_database('postgresql://postgres@localhost/name')
        database_exists('postgresql://postgres@localhost/name')  #=> True
    Supports checking against a constructed URL as well. ::
        engine = create_engine('postgresql://postgres@localhost/name')
        database_exists(engine.url)  #=> False
        create_database(engine.url)
        database_exists(engine.url)  #=> True
    """

    url = copy(make_url(url))
    database = url.database
    dialect_name = url.get_dialect().name

    def _sqlite_file_exists(database):
        if not os.path.isfile(database) or os.path.getsize(database) < 100:
            return False

        with open(database, "rb") as f:
            header = f.read(100)

        return header[:16] == b"SQLite format 3\x00"

    if dialect_name == "postgresql":
        text = "SELECT 1 FROM pg_database WHERE datname='%s'" % database
        for db in (database, "postgres", "template1", "template0", None):
            url = _set_url_database(url, database=db)
            engine = sa.create_engine(url, poolclass=NullPool)
            try:
                return bool(_get_scalar_result(engine, text))
            except (ProgrammingError, OperationalError):
                pass
        return False

    elif dialect_name == "mysql":
        url = _set_url_database(url, database=None)
        engine = sa.create_engine(url, poolclass=NullPool)
        text = (
            "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA "
            "WHERE SCHEMA_NAME = '%s'" % database
        )
        return bool(_get_scalar_result(engine, text))

    elif dialect_name == "sqlite":
        url = _set_url_database(url, database=None)
        engine = sa.create_engine(url, poolclass=NullPool)
        if database:
            return database == ":memory:" or _sqlite_file_exists(database)
        else:
            # The default SQLAlchemy database is in memory,
            # and :memory is not required, thus we should support that use-case
            return True
    else:
        text = "SELECT 1"
        try:
            engine = sa.create_engine(url, poolclass=NullPool)
            return bool(_get_scalar_result(engine, text))
        except (ProgrammingError, OperationalError):
            return False


def create_database(url, encoding="utf8", template=None):
    """Issue the appropriate CREATE DATABASE statement.
    :param url: A SQLAlchemy engine URL.
    :param encoding: The encoding to create the database as.
    :param template:
        The name of the template from which to create the new database. At the
        moment only supported by PostgreSQL driver.
    To create a database, you can pass a simple URL that would have
    been passed to ``create_engine``. ::
        create_database('postgresql://postgres@localhost/name')
    You may also pass the url from an existing engine. ::
        create_database(engine.url)
    Has full support for mysql, postgres, and sqlite. In theory,
    other database engines should be supported.
    """

    url = copy(make_url(url))
    database = url.database
    dialect_name = url.get_dialect().name
    dialect_driver = url.get_dialect().driver

    if dialect_name == "postgres":
        url = _set_url_database(url, database="postgres")
    elif dialect_name == "mssql":
        url = _set_url_database(url, database="master")
    elif not dialect_name == "sqlite":
        url = _set_url_database(url, database=None)

    if dialect_name == "mssql" and dialect_driver in {"pymssql", "pyodbc"}:
        engine = sa.create_engine(url, connect_args={"autocommit": True})
    elif dialect_name == "postgresql" and dialect_driver in {
        "asyncpg",
        "pg8000",
        "psycopg2",
        "psycopg2cffi",
    }:
        engine = sa.create_engine(url, isolation_level="AUTOCOMMIT")
    else:
        engine = sa.create_engine(url)

    if dialect_name == "postgresql":
        if not template:
            template = "template1"

        text = "CREATE DATABASE {0} ENCODING '{1}' TEMPLATE {2}".format(
            quote(engine, database), encoding, quote(engine, template)
        )

        with engine.connect() as connection:
            connection.execute(text)

    elif dialect_name == "mysql":
        text = "CREATE DATABASE {0} CHARACTER SET = '{1}'".format(
            quote(engine, database), encoding
        )
        with engine.connect() as connection:
            connection.execute(text)

    elif dialect_name == "sqlite" and database != ":memory:":
        if database:
            with engine.connect() as connection:
                connection.execute("CREATE TABLE DB(id int);")
                connection.execute("DROP TABLE DB;")

    else:
        text = "CREATE DATABASE {0}".format(quote(engine, database))
        with engine.connect() as connection:
            connection.execute(text)

    engine.dispose()


def drop_database(url):
    """Issue the appropriate DROP DATABASE statement.
    :param url: A SQLAlchemy engine URL.
    Works similar to the :ref:`create_database` method in that both url text
    and a constructed url are accepted. ::
        drop_database('postgresql://postgres@localhost/name')
        drop_database(engine.url)
    """

    url = copy(make_url(url))
    database = url.database
    dialect_name = url.get_dialect().name
    dialect_driver = url.get_dialect().driver

    if dialect_name == "postgres":
        url = _set_url_database(url, database="postgres")
    elif dialect_name == "mssql":
        url = _set_url_database(url, database="master")
    elif not dialect_name == "sqlite":
        url = _set_url_database(url, database=None)

    if dialect_name == "mssql" and dialect_driver in {"pymssql", "pyodbc"}:
        engine = sa.create_engine(url, connect_args={"autocommit": True})
    elif dialect_name == "postgresql" and dialect_driver in {
        "asyncpg",
        "pg8000",
        "psycopg2",
        "psycopg2cffi",
    }:
        engine = sa.create_engine(url, isolation_level="AUTOCOMMIT")
    else:
        engine = sa.create_engine(url)

    if dialect_name == "sqlite" and database != ":memory:":
        if database:
            os.remove(database)
    elif dialect_name == "postgresql":
        with engine.connect() as connection:
            # Disconnect all users from the database we are dropping.
            version = connection.dialect.server_version_info
            pid_column = "pid" if (version >= (9, 2)) else "procpid"
            text = """
            SELECT pg_terminate_backend(pg_stat_activity.%(pid_column)s)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '%(database)s'
            AND %(pid_column)s <> pg_backend_pid();
            """ % {
                "pid_column": pid_column,
                "database": database,
            }
            connection.execute(text)

            # Drop the database.
            text = "DROP DATABASE {0}".format(quote(connection, database))
            connection.execute(text)
    else:
        text = "DROP DATABASE {0}".format(quote(engine, database))
        with engine.connect() as connection:
            connection.execute(text)

    engine.dispose()


def _set_url_database(url: sa.engine.url.URL, database):
    if hasattr(sa.engine, "URL"):
        ret = sa.engine.URL.create(
            drivername=url.drivername,
            username=url.username,
            password=url.password,
            host=url.host,
            port=url.port,
            database=database,
            query=url.query,
        )
    else:  # SQLAlchemy <1.4
        url.database = database
        ret = url
    assert ret.database == database, ret
    return ret


def _get_scalar_result(engine, sql):
    with engine.connect() as conn:
        return conn.scalar(sql)
