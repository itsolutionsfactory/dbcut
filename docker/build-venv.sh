#!/bin/bash
set -e

python3 -m venv /venv

cd /app
source /venv/bin/activate
make init

rm -rf /root/.cache

find /app -name "*.pyc" -delete
find /venv -name "*.pyc" -delete
