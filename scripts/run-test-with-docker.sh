#!/usr/bin/env bash
ROOT_PROJECT="$(dirname "$(dirname "${BASH_SOURCE[0]}")")"

export PYTHON_IMAGE=${PYTHON_IMAGE:-python:3.6}
export POSTGRES_IMAGE=${POSTGRES_IMAGE:-postgres:9.6}
export MYSQL_IMAGE=${MYSQL_IMAGE:-mariadb:10.3}

echo "-------------------------------------------------------------------------------"
echo ""
echo "              python : ${PYTHON_IMAGE}"
echo "            postgres : ${POSTGRES_IMAGE}"
echo "               mysql : ${MYSQL_IMAGE}"
echo ""
echo "-------------------------------------------------------------------------------"

cd $ROOT_PROJECT


set -e
# docker-compose build
docker-compose down -v --remove-orphans 2> /dev/null
docker-compose run --rm dbcut_app make test
docker-compose down -v --remove-orphans 2> /dev/null
