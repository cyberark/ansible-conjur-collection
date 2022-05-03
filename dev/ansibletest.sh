#!/bin/bash -eu

cd ../../
DIR="ansible-conjur-collection/tests/output"
if [ -d "$DIR" ]; then
   echo "Existing '$DIR' found"
   rm -rf ansible-conjur-collection/tests/output
   echo "'$DIR' Directory has been deleted"
else
   echo "Warning: '$DIR' NOT found."
fi

mkdir -p ansible_collections/cyberark/
cd ansible_collections/cyberark/
git clone --single-branch --branch TestingPurposeOnly https://github.com/cyberark/ansible-conjur-collection.git
mv ansible-conjur-collection conjur
cd conjur
echo "Warning: Pooja 1"
pwd
ls
# pip install pycairo
pip install https://github.com/ansible/ansible/archive/stable-2.10.tar.gz --disable-pip-version-check
ansible-test units --docker default -v --python 3.8 tests/unit/plugins/lookup/test_conjur_variable.py
echo "Warning: Pooja 2"
pwd
ls
ansible-test units --docker default -v --python 3.8 --coverage
ansible-test coverage html -v --requirements --group-by command --group-by version
echo "Warning: Pooja 3"
cd ../../../
cp -r ansible_collections/cyberark/conjur/tests/output  ansible-conjur-collection/tests/
rm -rf ansible_collections
