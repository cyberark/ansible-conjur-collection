# ansible-conjur-collection Demo

## Requirements

* [Python 3](https://python.org)
* pip
  * `$ python3 -m ensurepip --upgrade`
* [Ansible](https://github.com/ansible/ansible)
* [Docker](https://docker.io)
  * `$ curl -fsSL get.docker.com | sh`
* Docker SDK for Python
  * `$ python3 -m pip install docker`
* community.general Ansible Collection
  * `$ ansible-galaxy collection install community.general`
* cyberark.conjur Ansible Collection
  * `$ ansible-galaxy collection install cyberark.conjur`

## Usage

### Deploy

```shell
ansible-playbook site.yml
```

### Architecture Overview

#### nginx_proxy

Hostname: `proxy`

This is the proxy where all requests should be sent to. Listening on port `443`, all requests will be proxied to `conjur_server`.

#### conjur_server

The Conjur appliance container.  Accepts HTTPS requests routed through `nginx_proxy` at the hostname `proxy`.

#### postgres_database

The database backend for secret and ACL storage. All data is encrypted using the `conjur_server` `CONJUR_DATA_KEY`.

#### conjur_client

The CLI client container to communicate directly to `conjur_server` using.

The CLI will already be authenticated to `conjur_server` by the end of deployment tasks.

Username: `admin`
Password: `CYberark11!!`

##### Access outside of container

`$ docker exec conjur_client conjur authn whoami`

##### Access from within container

```shell
$ docker exec -it conjur_client /bin/bash
root@cf497ec8fe6f:/# conjur authn whoami
```