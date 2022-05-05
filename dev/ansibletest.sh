#!/bin/bash -eu


cd ../

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
git clone --single-branch --branch ONYX-15264_ToReview https://github.com/cyberark/ansible-conjur-collection.git
mv ansible-conjur-collection conjur
cd conjur

# pip install pycairo
export PATH=/var/lib/jenkins/.local/bin:$PATH
pip install https://github.com/ansible/ansible/archive/devel.tar.gz --disable-pip-version-check
ansible-test units --docker default -v --python 3.8 tests/unit/plugins/lookup/test_conjur_variable.py --coverage
ansible-test coverage html -v --requirements --group-by command --group-by version
echo "Step 1"
pwd
ls
cd ../../../
echo "Step 2"
pwd
ls

cp -r ansible_collections/cyberark/conjur/tests/output tests
rm -rf ansible_collections

