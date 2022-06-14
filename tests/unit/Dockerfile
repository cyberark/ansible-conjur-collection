ARG PYTHON_VERSION
FROM python:${PYTHON_VERSION}

ARG ANSIBLE_VERSION
RUN pip install https://github.com/ansible/ansible/archive/${ANSIBLE_VERSION}.tar.gz --disable-pip-version-check

COPY tests/unit/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
