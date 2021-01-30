ARG FUNCTION_DIR="/home/app/"

FROM python:3.9-alpine as build-stage

ARG FUNCTION_DIR

RUN apk add build-base jpeg-dev zlib-dev libxml2-dev libxslt-dev make cmake libtool \
    autoconf \
    libexecinfo-dev \
    libcurl \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    openssl-dev \
    automake

RUN pip3 install awslambdaric

RUN pip3 install poetry

COPY poetry.lock ${FUNCTION_DIR}
COPY pyproject.toml ${FUNCTION_DIR}

WORKDIR ${FUNCTION_DIR}

RUN poetry config virtualenvs.create false
RUN poetry install --no-dev

FROM python:3.9-alpine

ARG FUNCTION_DIR

WORKDIR ${FUNCTION_DIR}

COPY --from=build-stage /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages

COPY . ${FUNCTION_DIR}

COPY --from=build-stage /usr/local/lib/*.so* /usr/local/lib/
COPY --from=build-stage /usr/lib/libxslt.so.1 \
    /usr/lib/libstdc++.so.6 \
    /usr/lib/libgcc_s.so.1 \
    /usr/lib/

ENTRYPOINT ["/usr/local/bin/python", "-m", "awslambdaric"]
CMD [ "main.handler" ]
