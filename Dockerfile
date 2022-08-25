FROM python:3-slim
LABEL maintainer="Backplane BV <backplane@users.noreply.github.com>"

COPY LICENSE requirements.txt /

RUN set -eux; \
  pip install -r /requirements.txt; \
  pip cache purge;

ARG NONROOT_UID=1000 NONROOT_GID=1000

RUN set -eux; \
  groupadd \
    --gid "$NONROOT_GID" \
    nonroot; \
  useradd \
    --home-dir "/work" \
    --shell "/bin/sh" \
    --uid "$NONROOT_UID" \
    --gid "nonroot" \
    --create-home \
    nonroot;

ENV PYTHONPATH="/app"
COPY src /app/

USER nonroot
WORKDIR /work

ENTRYPOINT ["/usr/local/bin/python3", "-m", "aws_reporter"]
