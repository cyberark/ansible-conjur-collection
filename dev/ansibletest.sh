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
git clone --single-branch --branch testjenkin_deleteit https://github.com/cyberark/ansible-conjur-collection.git
mv ansible-conjur-collection conjur
cd conjur

# pip install pycairo
export PATH=/var/lib/jenkins/.local/bin:$PATH
pip install https://github.com/ansible/ansible/archive/stable-2.10.tar.gz --disable-pip-version-check
ansible-test units --docker default -v --python 3.8 tests/unit/plugins/lookup/test_conjur_variable.py
# ansible-test coverage html -v --requirements --group-by command --group-by version

echo " know the variable 1"
pwd
ls
# export PATH=/var/lib/jenkins/.local/bin:$PATH
# pip install https://github.com/ansible/ansible/archive/stable-2.10.tar.gz --disable-pip-version-check
# ansible-test units --docker default -v --python 3.8 --coverage
# ansible-test coverage html -v --requirements --group-by command --group-by version

# echo " Testing 1 "
# ansible-test coverage erase
# ansible-test units --docker -v --color --python 3.8
# echo " Testing 2 "
# # ansible-test units --coverage
# echo " Testing 3 "
# ansible-test coverage html

# echo " know the variable 2"
# pwd   # /var/lib/jenkins/ansible_collections/cyberark/conjur
# ls
# echo " know the variable 2"
# cd ../../../
# echo " know the variable 4"
# pwd
# ls
# echo " know the variable 5"
# cp -r ansible_collections/cyberark/conjur/tests/output  ansible-conjur-collection/tests/
# rm -rf ansible_collections
