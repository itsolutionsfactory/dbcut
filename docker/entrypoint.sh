#!/usr/bin/env bash

wait-for-it testmysql_with_data:3306
wait-for-it testmysql_without_data:3306
wait-for-it testpostgres_without_data:5432

"$@"
