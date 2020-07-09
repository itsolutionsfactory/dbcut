ARG MYSQL_IMAGE

FROM $MYSQL_IMAGE

ADD docker/mysql_test/01-create-db.sh docker/mysql_test/02-dump.sql.gz /docker-entrypoint-initdb.d/
