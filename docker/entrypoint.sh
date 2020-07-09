#!/usr/bin/env bash
set -e

wait-for-it -t 120 ${POSTGRES_HOST}:5432
wait-for-it -t 120 ${MYSQL_HOST}:3306

"$@"
