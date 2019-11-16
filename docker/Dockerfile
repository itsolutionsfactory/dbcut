FROM python:3.6

ENV PYTHONUNBUFFERED 1
ENV PATH=/venv/bin:$PATH PYTHONPATH=${PYTHONPATH}:/app

ADD docker/entrypoint.sh /docker-entrypoint.sh
ADD docker/wait-for-it.sh /usr/local/bin/wait-for-it

ADD docker/build-base.sh /tmp/
RUN /bin/bash /tmp/build-base.sh

ADD . /app

ADD docker/build-venv.sh /tmp/
RUN /bin/bash /tmp/build-venv.sh

WORKDIR /app

ENTRYPOINT ["/docker-entrypoint.sh"]
