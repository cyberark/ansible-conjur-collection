ARG PYTHON_VERSION
FROM python:${PYTHON_VERSION}-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    apt-get clean

ARG ANSIBLE_VERSION
RUN pip install https://github.com/ansible/ansible/archive/${ANSIBLE_VERSION}.tar.gz --disable-pip-version-check --no-cache-dir

COPY tests/unit/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt --no-cache-dir
