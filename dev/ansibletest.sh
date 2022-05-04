#!/bin/bash -eu

echo "Step a"
pwd  # /var/lib/jenkins/workspace/ONYX-15263_withJenkinServerIssue
ls
cd ../../
echo "Step b"
pwd # /var/lib/jenkins
ls
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
git clone --single-branch --branch ONYX-15263_withJenkinServerIssue https://github.com/cyberark/ansible-conjur-collection.git
mv ansible-conjur-collection conjur
cd conjur

# pip install pycairo
export PATH=/var/lib/jenkins/.local/bin:$PATH
# pip install https://github.com/pygobject/pycairo/releases/download/v1.13.1/pycairo-1.13.1.tar.gz
pip install https://github.com/ansible/ansible/archive/devel.tar.gz --disable-pip-version-check
ansible-test units --docker default -v --python 3.8 tests/unit/plugins/lookup/test_conjur_variable.py

ansible-test units --docker default -v --python 3.8 --coverage
ansible-test coverage html -v --requirements --group-by command --group-by version
echo "Step 1"
pwd # /var/lib/jenkins/ansible_collections/cyberark/conjur
ls
cd ..
echo "Step 2"
pwd # /var/lib/jenkins/ansible_collections/cyberark
ls
cd ..
echo "Step 3"
pwd # /var/lib/jenkins/ansible_collections
ls
cd ..
echo "Step 4"
pwd # /var/lib/jenkins
ls
cp -r ansible_collections/cyberark/conjur/tests/output workspace/ONYX-15263_withJenkinServerIssue/tests
echo "Step 5"
pwd # /var/lib/jenkins
ls
rm -rf ansible_collections

# /var/lib/jenkins/workspace/ONYX-15263_withJenkinServerIssue

# var/lib/jenkins/ansible_collections/cyberark/conjur/tests/output/reports