#!/bin/bash
set -e

python3 -m venv /venv

cd /app
source /venv/bin/activate

pip install -U pip

pip install -r /app/requirements/base.txt
pip install -r /app/requirements/test.txt
pip install -r /app/requirements/postgresql.txt
pip install -r /app/requirements/mysql.txt

rm -rf /root/.cache

find /app -name "*.pyc" -delete
find /venv -name "*.pyc" -delete
