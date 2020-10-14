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

## Usage

### Deploy Conjur

```shell
ansible-playbook conjur.yml
```