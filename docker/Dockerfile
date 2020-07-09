ARG PYTHON_IMAGE

FROM $PYTHON_IMAGE

ENV PYTHONUNBUFFERED=1 \
    PYTHONBYTECODEBASE=/tmp/python \
    PATH=/venv/bin:$PATH

ADD docker/entrypoint.sh /docker-entrypoint.sh
ADD docker/wait-for-it.sh /usr/local/bin/wait-for-it

ADD docker/build-base.sh /tmp/
RUN /bin/bash /tmp/build-base.sh

ADD requirements /app/requirements
ADD docker/build-venv.sh /tmp/
RUN /bin/bash /tmp/build-venv.sh

WORKDIR /app

ADD . /app

ENTRYPOINT ["/docker-entrypoint.sh"]
