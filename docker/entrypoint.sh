#!/usr/bin/env bash
set -e

wait-for-it ${MYSQL_HOST}:3306
wait-for-it ${POSTGRES_HOST}:5432

"$@"
