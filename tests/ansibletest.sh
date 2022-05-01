#!/bin/bash -eu


DIR="/tests/output"
if [ -d "$DIR" ]; then
   echo "'$DIR' found , please delete it ..."
   rm -rf tests/output
else
   echo "Warning: '$DIR' NOT found."
fi
echo "Step 1 "
pwd
cd ..
echo "Step 2 "
pwd
cd ..
mkdir -p ansible_collections/cyberark/
cd ansible_collections/cyberark/
git clone --single-branch --branch ONYX-15264_ToReview https://github.com/cyberark/ansible-conjur-collection.git

mv ansible-conjur-collection conjur
cd conjur

pip install pycairo
pip install https://github.com/ansible/ansible/archive/stable-2.10.tar.gz --disable-pip-version-check
# ansible-test units --docker default -v --python 3.8 --coverage
ansible-test coverage html -v --requirements --group-by command --group-by version

# cp -r /tests/output  /ansible-conjur-collection/tests/
echo "Step first"
pwd
ls
cd ..
echo "Step second"
pwd
# cd ..

ls
echo "Step third "
cd ..
pwd
echo "Step Third"
cd ..
pwd
cp -r ansible_collections/cyberark/conjur/tests/output  ansible-conjur-collection/tests/
rm -rf ansible_collections
