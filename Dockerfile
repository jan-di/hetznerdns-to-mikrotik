FROM docker.io/python:3.13-alpine

RUN pip3 install poetry

WORKDIR /app

COPY pyproject.toml poetry.lock poetry.toml .
RUN poetry install

COPY . .
RUN poetry install

ENTRYPOINT ["poetry", "run", "hdns2mikrotik"]


