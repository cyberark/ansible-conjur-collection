ARG PYTHON_VERSION
FROM python:${PYTHON_VERSION}-slim

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /cyberark

# install ansible and its test tool
ARG ANSIBLE_VERSION
RUN pip3 install ansible==${ANSIBLE_VERSION}.* pytest-testinfra

# install docker installation requirements
RUN apt-get update && \
    apt-get install -y ca-certificates \
                       curl \
                       gnupg

# install docker
RUN install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    chmod a+r /etc/apt/keyrings/docker.gpg
RUN echo \
    "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
    "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
    tee /etc/apt/sources.list.d/docker.list > /dev/null
RUN apt-get update && \
    apt-get -y install docker-ce
