#!/usr/bin/env python
from click.testing import CliRunner
from dbcut.cli.main import main

DEFAULT_YML = """
cache: .cache/dbcut

default_limit: 10
default_backref_limit: 50

default_backref_depth: 2
default_join_depth: 3

global_exclude:
  - django_admin_log
  - django_session

queries:
  - from: auth_group
    backref_depth: 3

  - from: django_migrations
    limit: no
  - from: django_content_type
  - from: django_session

  - from: customer_customer
    backref_depth: 0
    join_depth: 0
    where:
      country: France

  - from: customer_customer
    backref_depth: 5
    join_depth: 7
    where:
      country: USA
    order-by: -last_name
    offset: 2
    limit: 10

  - from: employee_employee
    order-by:
      - -hire_date
      - last_name
  - from: customer_invoice

  - from: customer_invoiceline
  - from: customer_playlist
  - from: customer_playlist_customer
  - from: customer_playlist_track
  - from: music_album
  - from: music_artist
  - from: music_composer
  - from: music_genre
  - from: music_mediatype
  - from: music_track
  - from: music_track_composer

  - from: customer_playlist
    include:
      - music_track
      - music_artist
    where:
      $or:
        music_track.title: 'Ugly In The Morning'
        $in:
          music_artist.name: ['AC/DC', 'Amy Winehouse']
"""

mysql_mysql_databases = """
databases:
  source_uri: mysql://${DB_USER}:${DB_PASSWORD}@testmysql_with_data/${DB_NAME}
  destination_uri: mysql://${DB_USER}:${DB_PASSWORD}@testmysql_without_data/${DB_NAME}
"""

mysql_sqlite_databases = """
databases:
  source_uri: mysql://${DB_USER}:${DB_PASSWORD}@testmysql_with_data/${DB_NAME}
  destination_uri: sqlite:///test-db.db
"""

mysql_postgres_databases = """
databases:
  source_uri: mysql://${DB_USER}:${DB_PASSWORD}@testmysql_with_data/${DB_NAME}
  destination_uri: postgresql://${DB_USER}:${DB_PASSWORD}@testpostgres_without_data/${DB_NAME}
"""

mysql_mysql_databases = """
databases:
  source_uri: mysql://${DB_USER}:${DB_PASSWORD}@testmysql_with_data/${DB_NAME}
  destination_uri: mysql://${DB_USER}:${DB_PASSWORD}@testmysql_without_data/${DB_NAME}
"""

mysql_sqlite_databases = """
databases:
  source_uri: mysql://${DB_USER}:${DB_PASSWORD}@testmysql_with_data/${DB_NAME}
  destination_uri: sqlite:///test-db.db
"""

mysql_postgres_databases = """
databases:
  source_uri: mysql://${DB_USER}:${DB_PASSWORD}@testmysql_with_data/${DB_NAME}
  destination_uri: postgresql://${DB_USER}:${DB_PASSWORD}@testpostgres_without_data/${DB_NAME}
"""


def do_cmd_test(database_yaml, cmd_name, *options):
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("dbcut.yml", "w") as f:
            f.write(database_yaml)
            f.write(DEFAULT_YML)
        result = runner.invoke(
            main,
            ["-y", "-c", "dbcut.yml", cmd_name] + list(options),
            catch_exceptions=False,
        )
        if not result.exit_code == 0:
            print(result.output)
        assert result.exit_code == 0


def test_load_mysql_to_mysql():
    do_cmd_test(mysql_mysql_databases, "load")


def test_load_mysql_to_sqlite():
    do_cmd_test(mysql_sqlite_databases, "load")


def test_load_mysql_to_postgres():
    do_cmd_test(mysql_postgres_databases, "load")


def test_dumpjson_mysql_to_mysql():
    do_cmd_test(mysql_mysql_databases, "dumpjson")


def test_dumpjson_mysql_to_sqlite():
    do_cmd_test(mysql_sqlite_databases, "dumpjson")


def test_dumpjson_mysql_to_postgres():
    do_cmd_test(mysql_postgres_databases, "dumpjson")


def test_dumpsql_mysql_to_mysql():
    do_cmd_test(mysql_mysql_databases, "dumpsql")


def test_dumpsql_mysql_to_sqlite():
    do_cmd_test(mysql_sqlite_databases, "dumpsql")


def test_dumpsql_mysql_to_postgres():
    do_cmd_test(mysql_postgres_databases, "dumpsql")


def test_inspect_mysql_to_mysql():
    do_cmd_test(mysql_mysql_databases, "inspect")


def test_inspect_mysql_to_sqlite():
    do_cmd_test(mysql_sqlite_databases, "inspect")


def test_inspect_mysql_to_postgres():
    do_cmd_test(mysql_postgres_databases, "inspect")


def test_flush_mysql_to_mysql():
    do_cmd_test(mysql_mysql_databases, "flush")


def test_flush_mysql_to_sqlite():
    do_cmd_test(mysql_sqlite_databases, "flush")


def test_flush_mysql_to_postgres():
    do_cmd_test(mysql_postgres_databases, "flush")


def test_clear_mysql_to_mysql():
    do_cmd_test(mysql_mysql_databases, "clear")


def test_clear_mysql_to_sqlite():
    do_cmd_test(mysql_sqlite_databases, "clear")


def test_clear_mysql_to_postgres():
    do_cmd_test(mysql_postgres_databases, "clear")


# def test_multiple_cmd_mysql_to_mysql():
#     do_cmd_test(mysql_mysql_databases, "flush ")


# def test_multiple_cmd_mysql_to_sqlite():
#     do_cmd_test(mysql_sqlite_databases, "multiple_cmd")


# def test_multiple_cmd_mysql_to_postgres():
#     do_cmd_test(mysql_postgres_databases, "multiple_cmd")
