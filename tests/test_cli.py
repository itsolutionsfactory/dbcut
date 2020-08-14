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
  source_uri: mysql://${MYSQL_USER}:${MYSQL_PASSWORD}@${MYSQL_HOST}/${MYSQL_DATABASE}
  destination_uri: mysql://${MYSQL_USER}:${MYSQL_PASSWORD}@${MYSQL_HOST}/${MYSQL_DATABASE_2}
"""

mysql_sqlite_databases = """
databases:
  source_uri: mysql://${MYSQL_USER}:${MYSQL_PASSWORD}@${MYSQL_HOST}/${MYSQL_DATABASE}
  destination_uri: sqlite:///${SQLITE_DB}
"""

mysql_postgres_databases = """
databases:
  source_uri: mysql://${MYSQL_USER}:${MYSQL_PASSWORD}@${MYSQL_HOST}/${MYSQL_DATABASE}
  destination_uri: postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}/${POSTGRES_DB_2}
"""


def do_invoke_test(runner, *args, **kwargs):
    kwargs.setdefault("catch_exceptions", False)
    result = runner.invoke(*args, **kwargs)
    if not result.exit_code == 0:
        print(result.output)
    assert result.exit_code == 0


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


def test_clear_mysql_to_mysql():
    do_cmd_test(mysql_mysql_databases, "clear")


def test_clear_mysql_to_sqlite():
    do_cmd_test(mysql_sqlite_databases, "clear")


def test_clear_mysql_to_postgres():
    do_cmd_test(mysql_postgres_databases, "clear")


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


def test_loading_cache():
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("dbcut.yml", "w") as f:
            f.write(mysql_mysql_databases)
            f.write(DEFAULT_YML)

        do_invoke_test(runner, main, ["-y", "load"])
        do_invoke_test(runner, main, ["-y", "load"])
        do_invoke_test(runner, main, ["-y", "load", "--force-refresh"])
        do_invoke_test(runner, main, ["-y", "load", "--no-cache"])
        do_invoke_test(runner, main, ["-y", "purgecache"])


def test_multiple_cmd_mysql_to_mysql():
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("dbcut.yml", "w") as f:
            f.write(mysql_mysql_databases)
            f.write(DEFAULT_YML)

        do_invoke_test(
            runner,
            main,
            ["-y", "purgecache", "flush", "load", "--only", "employee_employee"],
        )


def test_expand_env_variables():
    runner = CliRunner()
    mysql_mysql_databases = """
databases:

  source_uri: mysql://${XXXMYSQL_USER}:${MYSQL_PASSWORD}@${MYSQL_HOST}/${MYSQL_DATABASE}
  destination_uri: sqlite:///${SQLITE_DB}
"""
    with runner.isolated_filesystem():
        with open("dbcut.yml", "w") as f:
            f.write(mysql_mysql_databases)
            f.write(DEFAULT_YML)

        result = runner.invoke(main, ["-y", "load"])
        assert not result.exit_code == 0
        print(result.output)
        assert "XXXMYSQL_USER" in result.output
