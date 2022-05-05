#!/bin/bash -eu

# currentbranch=$(git symbolic-ref HEAD | sed -e 's,.*/\(.*\),\1,')

# currentbranch=$(git branch --no-color 2> /dev/null | sed -e '/^[^*]/d' -e "s/* \(.*\)/\1$(parse_git_dirty)/")
currentbranch=$(git branch 2>/dev/null | grep '^*' | colrm 1 2)
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
git clone --single-branch --branch "$currentbranch" https://github.com/cyberark/ansible-conjur-collection.git
mv ansible-conjur-collection conjur
cd conjur

# pip install pycairo
export PATH=/var/lib/jenkins/.local/bin:$PATH
pip install https://github.com/ansible/ansible/archive/devel.tar.gz --disable-pip-version-check
ansible-test units --docker default -v --python 3.8 tests/unit/plugins/lookup/test_conjur_variable.py --coverage
ansible-test coverage html -v --requirements --group-by command --group-by version
cd ../../../

CURRENTDIR="workspace"
if [ -d "$CURRENTDIR" ]; then
   rootdir="_-ansible-conjur-collection_"
   Combinedstring=$rootdir$currentbranch
   get32characters=${Combinedstring: -32}
   echo " Combined string is '$get32characters' "
   cp -r ansible_collections/cyberark/conjur/tests/output workspace/"$get32characters"/tests
else
   cp -r ansible_collections/cyberark/conjur/tests/output ansible-conjur-collection/tests
fi

rm -rf ansible_collections
