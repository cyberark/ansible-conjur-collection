FROM ubuntu:latest

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /ansible_collections/cyberark/conjur

# install python 3
RUN apt-get update && \
    apt-get install -y python3-pip && \
    pip3 install --upgrade pip

# install ansible and its test tool
RUN pip3 install ansible pytest-testinfra

# install docker installation requirements
RUN apt-get update && \
    apt-get install -y apt-transport-https \
                       ca-certificates \
                       curl \
                       software-properties-common

# install docker
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
RUN add-apt-repository \
       "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
       $(lsb_release -cs) \
       stable"

RUN apt-get update && \
    apt-get -y install docker-ce

COPY . /ansible_collections/cyberark

# COPY /ansible_collections/cyberark/ansible-conjur-collection /ansible_collections/cyberark/conjur

# RUN rm -r /ansible_collections/cyberark/ansible-conjur-collection

# RUN pip install https://github.com/ansible/ansible/archive/stable-2.9.tar.gz --disable-pip-version-check
# RUN ansible-test units --docker default -v --python 3.8 —coverage
# RUN ansible-test coverage html -v --requirements --group-by command --group-by version
