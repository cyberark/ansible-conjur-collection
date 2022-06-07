ARG PYTHON_VERSION
FROM python:${PYTHON_VERSION}

ARG ANSIBLE_VERSION
RUN pip install https://github.com/ansible/ansible/archive/${ANSIBLE_VERSION}.tar.gz --disable-pip-version-check && \
    pip install coverage \
                mock \
                pytest \
                pytest-mock \
                pytest-xdist \
                pytest-forked \
                pyyaml \
                bcrypt \
                passlib \
                pexpect \
                pytz \
                pywinrm
