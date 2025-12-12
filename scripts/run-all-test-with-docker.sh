#!/usr/bin/env bash
set -e
ROOT_PROJECT="$(dirname "$(dirname "${BASH_SOURCE[0]}")")"

cd "$ROOT_PROJECT"

# Define Python versions to test
PYTHON_VERSIONS=("3.10" "3.11" "3.12")

# Database versions
export POSTGRES_IMAGE=${POSTGRES_IMAGE:-postgres:9.6}
export MYSQL_IMAGE=${MYSQL_IMAGE:-mariadb:10.3}

_print() { printf "\033[1;32m%b\033[0m\n" "$1"; }

# Function to run tests for a specific Python version
run_test_for_version() {
    local python_version=$1
    _print "==============================================================================="
    _print "Testing with Python ${python_version}"
    _print "==============================================================================="

    export PYTHON_IMAGE="python:${python_version}"
    bash "${ROOT_PROJECT}/scripts/run-test-with-docker.sh"

    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        _print "✓ Python ${python_version} tests passed"
    else
        _print "✗ Python ${python_version} tests failed"
        return $exit_code
    fi
}

# Check if xpanes is available for parallel execution
if type "xpanes" &> /dev/null; then
    _print "Running tests in parallel with xpanes"
    declare -a CMDS
    for version in "${PYTHON_VERSIONS[@]}"; do
        CMDS+=("PYTHON_IMAGE=python:${version} POSTGRES_IMAGE=${POSTGRES_IMAGE} MYSQL_IMAGE=${MYSQL_IMAGE} bash scripts/run-test-with-docker.sh")
    done

    xpanes --desync -t -e "${CMDS[@]}"
else
    _print "Running tests sequentially"
    failed_versions=()

    for version in "${PYTHON_VERSIONS[@]}"; do
        if ! run_test_for_version "$version"; then
            failed_versions+=("$version")
        fi
        echo ""
    done

    # Summary
    _print "==============================================================================="
    _print "Test Summary"
    _print "==============================================================================="

    if [ ${#failed_versions[@]} -eq 0 ]; then
        _print "✓ All Python versions passed: ${PYTHON_VERSIONS[*]}"
        exit 0
    else
        _print "✗ Failed versions: ${failed_versions[*]}"
        _print "✓ Passed versions: $(printf '%s\n' "${PYTHON_VERSIONS[@]}" | grep -v -F "$(printf '%s\n' "${failed_versions[@]}")" | tr '\n' ' ')"
        exit 1
    fi
fi
