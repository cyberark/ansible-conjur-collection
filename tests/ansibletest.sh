#!/bin/bash -ex
cd ../../
mkdir -p ansible_collections/cyberark/conjur
cp -r ansible-conjur-collection/ ansible_collections/cyberark/conjur
cd ansible_collections/cyberark/conjur

pip install https://github.com/ansible/ansible/archive/stable-2.9.tar.gz --disable-pip-version-check
ansible-test units --docker default -v --python 3.8 --coverage
ansible-test coverage html -v --requirements --group-by command --group-by version

cp -r ansible-conjur-collection/ ansible_collections/cyberark/conjur
