#!/bin/bash -eu

mkdir -p ansible_collections/cyberark/
cd ansible_collections/cyberark/
git clone --single-branch --branch test_it https://github.com/cyberark/ansible-conjur-collection.git

mv ansible-conjur-collection conjur
cd conjur

# pip install pycairo
pip install https://github.com/ansible/ansible/archive/stable-2.10.tar.gz --disable-pip-version-check

ansible-test units --docker default -v --python 3.8 --coverage
ansible-test coverage html -v --requirements --group-by command --group-by version