# syntax=docker/dockerfile:1
ARG PYTHON_VERSION
FROM python:${PYTHON_VERSION:-3.12}-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    apt-get clean

ARG ANSIBLE_VERSION
COPY tests/requirements-ansible-core-2.17.txt \
     tests/requirements-ansible-core-2.18.txt \
     tests/requirements-ansible-core-2.19.txt \
     /tmp/
RUN --mount=type=secret,id=pip_conf,target=/root/.pip/pip.conf,required=true \
    pip install --require-hashes -r /tmp/requirements-ansible-core-${ANSIBLE_VERSION}.txt \
    --disable-pip-version-check --no-cache-dir

COPY tests/unit/requirements.txt /tmp/requirements.txt
RUN --mount=type=secret,id=pip_conf,target=/root/.pip/pip.conf,required=true \
    pip install --require-hashes -r /tmp/requirements.txt --no-cache-dir
