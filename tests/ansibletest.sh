#!/bin/bash -ex

mkdir -p ansible_collections/cyberark/
cd ansible_collections/cyberark/
git clone --single-branch --branch to_testonly https://github.com/cyberark/ansible-conjur-collection.git

mv ansible-conjur-collection conjur
cd conjur
# pip install --user git+https://github.com/pygobject/pycairo.git
pip install https://github.com/ansible/ansible/archive/stable-2.10.tar.gz --disable-pip-version-check
ansible-galaxy collection install ansible.netcommon ansible.utils -p .
ansible-test units -v --color --docker --coverage
# ansible-test units --docker default -v --python 3.8 --coverage
ansible-test coverage html -v --requirements --group-by command --group-by version
# ansible-test coverage html


