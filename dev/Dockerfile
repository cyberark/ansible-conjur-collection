ARG PYTHON_VERSION
FROM python:${PYTHON_VERSION:-3.12}-slim

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /cyberark

# Install Ansible and its test tool
ARG ANSIBLE_VERSION
RUN pip3 install ansible==${ANSIBLE_VERSION}.* pytest-testinfra --no-cache-dir

# Install Docker dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Add Docker's official GPG key and repository, dynamically setting architecture
RUN install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    chmod a+r /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list

# Install Docker CLI and plugins
RUN apt-get update && \
    apt-get -y install docker-ce-cli docker-buildx-plugin && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set up Ansible collection
RUN mkdir -p /cyberark/collections

COPY cyberark-conjur-*tar.gz /cyberark/collections

RUN FILE_NAME=$(find /cyberark/collections -name "cyberark-conjur-*tar.gz") && \
    ansible-galaxy collection install "$FILE_NAME" --force
