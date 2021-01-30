FROM python:3.9-alpine as build-stage

ARG FUNCTION_DIR="/home/app/"

RUN apk add build-base jpeg-dev zlib-dev libxml2-dev libxslt-dev postgresql-libs make cmake libtool \
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

COPY poetry.lock /home/app/
COPY pyproject.toml /home/app/

WORKDIR /home/app/

RUN poetry config virtualenvs.create false
RUN poetry install --no-dev

COPY . /home/app/

ENV DJANGO_SETTINGS_MODULE=pycon.settings.prod

ENTRYPOINT ["/usr/local/bin/python", "-m", "awslambdaric"]
CMD [ "main.handler" ]
