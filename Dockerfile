FROM docker.io/python:3.14-alpine

RUN pip3 install poetry

WORKDIR /app

COPY pyproject.toml poetry.lock poetry.toml .
RUN poetry install --with main --no-root

COPY . .
RUN poetry install --with main

ENTRYPOINT ["poetry", "run", "hdns2mikrotik"]


