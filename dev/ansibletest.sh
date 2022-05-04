#!/bin/bash -eu


cd ../../

DIR="ansible-conjur-collection/tests/output"
if [ -d "$DIR" ]; then
   echo "Existing '$DIR' found"
   rm -rf ansible-conjur-collection/tests/output
   echo "'$DIR' Directory has been deleted"
else
   echo "Warning: '$DIR' NOT found. "
fi

mkdir -p ansible_collections/cyberark/
cd ansible_collections/cyberark/
git clone --single-branch --branch ONYX-15263 https://github.com/cyberark/ansible-conjur-collection.git
mv ansible-conjur-collection conjur
cd conjur
echo "Step q"
pwd
ls
# pip install pycairo
export PATH=/var/lib/jenkins/.local/bin:$PATH
echo "Step p"
pip install https://github.com/ansible/ansible/archive/devel.tar.gz --disable-pip-version-check
echo "Step a"
ansible-test units --docker default -v --python 3.8 --coverage
echo "Step b"
ansible-test coverage html -v --requirements --group-by command --group-by version
cd ..
echo "Step 1"
pwd
ls
cd ../../
echo "Step 2"
pwd
ls
# DIR="workspace"
# if [ -d "$DIR" ]; then
#    cp -r ansible_collections/cyberark/conjur/tests/output workspace/ONYX-15263/tests
# else
#    cp -r ansible_collections/cyberark/conjur/tests/output ansible-conjur-collection/tests
# fi

# rm -rf ansible_collections
