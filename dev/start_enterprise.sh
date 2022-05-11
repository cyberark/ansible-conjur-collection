#!/bin/bash
set -x
set -e

# Script to run SpringBootExample against Conjur Enterprise (appliance)

# Ensure conjur-intro submodule is checked out
# git submodule update --init --recursive

# pushd ./conjur-intro
#   pwd

  cd conjur-intro

  # Provision master and follower
  ./bin/dap --provision-master
  ./bin/dap --provision-follower

  # Load policy required by SpringBootExample
  # conjur.yml must be in the conjur-intro folder for access
  # via docker-compose exec
  cp ../policy/root.yml .
  # cp ../conjur.yml .
  ./bin/cli conjur policy load --replace root root.yml

  # # # Set variable values
#   ./bin/cli conjur variable values add db/password secret
#   ./bin/cli conjur variable values add db/dbuserName 123456
#   ./bin/cli conjur variable values add db/dbpassWord 7890123
#   ./bin/cli conjur variable values add db/key 456789

#   ./bin/cli conjur policy load root /policy/root.yml
  ./bin/cli conjur variable values add ansible/test-secret test_secret_password
  ./bin/cli conjur variable values add ansible/test-secret-in-file test_secret_in_file_password
  ./bin/cli conjur variable values add ansible/target-password target_secret_password
#   ./bin/cli conjur variable values add "ansible/var with spaces" var_with_spaces_secret_password


  # Retrieve pem
  docker-compose  \
    run \
    --rm \
    -w /src/cli \
    --entrypoint /bin/bash \
    conjur_cli \
      -c "cp /root/conjur-demo.pem conjur-enterprise.pem"
  cp conjur-enterprise.pem ../



  # Retrieve Admin API Key
  admin_api_key="$(./bin/cli conjur user rotate_api_key|tail -n 1| tr -d '\r')"
  echo "admin api key: ${admin_api_key}"
  echo "${admin_api_key}" > api_key
  cp api_key ../

cd ..
# popd
pwd


filepath=$(pwd)
firstthree=${filepath:1:3}

if [ "$firstthree" == var ]; then
   currentbranch=$BRANCH_NAME
else
   currentbranch=$(git branch | sed -n -e 's/^\* \(.*\)/\1/p')
fi


cd ../../
DIR="ansible-conjur-collection/tests/output"
if [ -d "$DIR" ]; then
   echo "Existing '$DIR' found"
   rm -rf ansible-conjur-collection/tests/output
else
   echo "'$DIR' NOT found. "
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
   cp -r ansible_collections/cyberark/conjur/tests/output workspace/"$get32characters"/tests
else
   cp -r ansible_collections/cyberark/conjur/tests/output ansible-conjur-collection/tests
fi

rm -rf ansible_collections






# docker run \
#   --volume "$(git rev-parse --show-toplevel):/repo" \
#   --volume "${PWD}/maven_cache":/root/.m2 \
#   --volume "${PWD}/api_key:/api_key" \
#   --volume "${PWD}/conjur-enterprise.pem:/conjur-enterprise.pem" \
#   --network dap_net \
#   -e "CONJUR_APPLIANCE_URL=https://conjur-master.mycompany.local" \
#   -e "CONJUR_ACCOUNT=demo" \
#   -e "CONJUR_AUTHN_LOGIN=admin" \
#   -e "CONJUR_AUTHN_API_KEY=${admin_api_key}" \
#   -e "CONJUR_CERT_FILE=/conjur-enterprise.pem" \
#   -e "CONJUR_AUTHN_TOKEN_FILE=/api_key" \
#   --workdir "/repo" \
#   --rm \
#   --entrypoint /bin/bash \
#   sampleapp \
#     -ec 'mvn --batch-mode -f pom.xml jacoco:prepare-agent test jacoco:report'