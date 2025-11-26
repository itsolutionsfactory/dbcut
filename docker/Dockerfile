ARG PYTHON_IMAGE

FROM $PYTHON_IMAGE

ENV PYTHONUNBUFFERED=1 \
    PYTHONBYTECODEBASE=/tmp/python \
    PATH=/venv/bin:$PATH \
    UV_PROJECT_ENVIRONMENT="/usr/local/"

# Install build dependencies
COPY docker/build-base.sh /tmp/
RUN /bin/bash /tmp/build-base.sh

# Install uv
RUN curl -LsSf https://astral.sh/uv/0.9.12/install.sh | sh
ENV PATH=/root/.local/bin:$PATH

COPY docker/entrypoint.sh /docker-entrypoint.sh
COPY docker/wait-for-it.sh /usr/local/bin/wait-for-it

WORKDIR /app

ADD . /app

RUN uv lock --check
RUN uv sync --frozen --no-cache --all-groups --all-extras

ENTRYPOINT ["/docker-entrypoint.sh"]
