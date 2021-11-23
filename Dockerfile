FROM python:3-slim
LABEL maintainer="Backplane BV <backplane@users.noreply.github.com>"

COPY reporter.py requirements.txt LICENSE /app/

RUN set -eux; \
  pip install -r /app/requirements.txt; \
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

USER nonroot
WORKDIR /work

ENTRYPOINT ["/app/reporter.py"]
