ARG PYTHON_VERSION
FROM python:${PYTHON_VERSION:-3.12}-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    apt-get clean

ARG ANSIBLE_VERSION
# ansible-core and test dependencies are installed from a hash-pinned lock file
# (one per Ansible matrix entry). Regenerate with dev/update_test_locks.sh.
COPY tests/requirements/ansible-${ANSIBLE_VERSION}.txt /tmp/requirements.txt
RUN pip install --require-hashes -r /tmp/requirements.txt --disable-pip-version-check --no-cache-dir
