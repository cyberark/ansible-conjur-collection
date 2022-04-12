#!/bin/bash -ex

mkdir -p ansible_collections/cyberark/
cd ansible_collections/cyberark/
git clone --single-branch --branch to_testonly https://github.com/cyberark/ansible-conjur-collection.git

mv ansible-conjur-collection conjur
cd conjur
# pip install --user git+https://github.com/pygobject/pycairo.git

# export PATH="${PATH}:/Users/caio.hc.oliveira/Library/Python/3.7/bin"
# export PYTHONPATH="${PYTHONPATH}:/Users/caio.hc.oliveira/Library/Python/3.7/bin"

pip install https://github.com/ansible/ansible/archive/stable-2.10.tar.gz --disable-pip-version-check

# sudo apt install libgirepository1.0-dev gcc libcairo2-dev pkg-config python3-dev gir1.2-gtk-3.0
pip install pycairo
# pip3 install PyGObject

# ansible-galaxy collection install ansible.netcommon ansible.utils -p .
# ansible-test units -v --color --docker --coverage
ansible-test units --docker default -v --python 3.8 --coverage
ansible-test coverage html -v --requirements --group-by command --group-by version
# ansible-test coverage html


