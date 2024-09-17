#!/usr/bin/env bash
ROOT_PROJECT="$(dirname "$(dirname "${BASH_SOURCE[0]}")")"

if ! command -v "docker-compose" >/dev/null
then
    compose="docker compose"
else
    compose="docker-compose"
fi


export PYTHON_IMAGE=${PYTHON_IMAGE:-python:3.6}
export POSTGRES_IMAGE=${POSTGRES_IMAGE:-postgres:9.6}
export MYSQL_IMAGE=${MYSQL_IMAGE:-mariadb:10.3}
export PROJECT_DIR=${TRAVIS_BUILD_DIR:-${CI_PROJECT_DIR:-$(git rev-parse --show-toplevel)}}
export JOB_ID=$(echo ${TRAVIS_JOB_ID:-${CI_JOB_ID:-${TMUX_PANE:-"1"}}} | sed 's/[^0-9]*//g')

export COMPOSE_PROJECT_NAME=dbcut_test_${JOB_ID}

if [ -z "$CI_JOB_ID" ]; then
    export ROOT_VOLUME_PATH=${ROOT_PROJECT}
else
    JOB_CONTAINER_ID=$(docker ps -q -f "label=com.gitlab.gitlab-runner.job.id=${CI_JOB_ID}")
    BUILDS_VOLUME_SOURCE=$(docker inspect $JOB_CONTAINER_ID | jq '.[].Mounts | .[] | select(.Destination=="/builds") | .Source' | sed 's/"//g')
    export ROOT_VOLUME_PATH="${BUILDS_VOLUME_SOURCE}/${CI_PROJECT_PATH}"
fi

echo "-------------------------------------------------------------------------------"
echo ""
echo "              python : ${PYTHON_IMAGE}"
echo "            postgres : ${POSTGRES_IMAGE}"
echo "               mysql : ${MYSQL_IMAGE}"
echo "              job_id : ${JOB_ID}"
echo "         project dir : ${PROJECT_DIR}"
echo ""
echo "-------------------------------------------------------------------------------"

cd "$ROOT_PROJECT" || exit

_print() { printf "\033[1;32m%b\033[0m\n" "$1"; }

_cleanup() {
    _print ":: Cleanup"
    $compose down -v --remove-orphans
}

if [ "$1" = "cleanup" ]; then
    _cleanup
else
    trap _cleanup EXIT
    trap '{ exit 1; }' TERM INT

    _cleanup

    _print ":: Building image"
    $compose build

    _print ":: Running tests"
    $compose run --rm app make test
fi
