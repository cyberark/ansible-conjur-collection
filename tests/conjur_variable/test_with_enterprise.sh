#!/bin/bash -eu

# set -o pipefail

# function cleanup {
#   echo 'Removing test environment'
#   echo '---'
#   docker-compose down -v
# }

# trap cleanup EXIT

# cleanup

# normalises project name by filtering non alphanumeric characters and transforming to lowercase
declare -x COMPOSE_PROJECT_NAME
COMPOSE_PROJECT_NAME=$(echo "${BUILD_TAG:-ansible-plugin-testing}-conjur-variable" | sed -e 's/[^[:alnum:]]//g' | tr '[:upper:]' '[:lower:]')

declare -x ANSIBLE_MASTER_AUTHN_API_KEY=''
declare -x CONJUR_ADMIN_AUTHN_API_KEY=''
declare -x ANSIBLE_CONJUR_CERT_FILE=''

# function main() {
# #   docker-compose up -d --build conjur \
# #                                conjur_https \
# #                                conjur_cli \

echo " Step 1 "
pwd
ls

git clone --single-branch --branch main https://github.com/conjurdemos/conjur-intro.git
cd conjur-intro
echo " Provision Master"
  ./bin/dap --provision-master
  ./bin/dap --provision-follower
echo " Step 2 "
pwd
ls
echo " Setup Policy "
  # cp ../policy/root.yml .

  cd ..

  # cp -r ansible_collections/cyberark/conjur/tests/output ansible-conjur-collection/tests
  cp -r policy/root.yml conjur-intro
  cd conjur-intro
echo " Step 2 "
pwd
ls
  ./bin/cli conjur policy load --replace root root.yml
  ./bin/cli conjur variable values add ansible/test-secret test_secret_password
  ./bin/cli conjur variable values add ansible/test-secret-in-file test_secret_in_file_password
  ./bin/cli conjur variable values add ansible/target-password target_secret_password

echo " Setup CLI "

  docker-compose  \
    run \
    --rm \
    -w /src/cli \
    --entrypoint /bin/bash \
    conjur_cli \
      -c "cp /root/conjur-demo.pem conjur-enterprise.pem"
  cp conjur-enterprise.pem ../

  admin_api_key="$(./bin/cli conjur user rotate_api_key|tail -n 1| tr -d '\r')"
  echo "admin api key: ${admin_api_key}"
  echo "${admin_api_key}" > api_key
  cp api_key ../

  cd ..

  echo "Waiting for Conjur server to come up"
  # wait_for_conjur

#   echo "Fetching SSL certs"
#   fetch_ssl_certs

#   echo "Fetching admin API key"
#   CONJUR_ADMIN_AUTHN_API_KEY=$(docker-compose exec -T conjur conjurctl role retrieve-key cucumber:user:admin)

#   echo "Recreating conjur CLI with admin credentials"
#   docker-compose up -d conjur_cli

#   echo "Configuring Conjur via CLI"
#   setup_conjur

#   echo "Fetching Ansible master host credentials"
#   ANSIBLE_MASTER_AUTHN_API_KEY=$(docker-compose exec -T conjur_cli conjur host rotate_api_key --host ansible/ansible-master)
#   ANSIBLE_CONJUR_CERT_FILE='/cyberark/tests/conjur.pem'

#   echo "Get Access Token"
#   setup_access_token

#   echo "Preparing Ansible for test run"
#   docker-compose up -d --build ansible

#   echo "Running tests"
#   run_test_cases
# }

# function wait_for_conjur {
#   docker-compose exec -T conjur conjurctl wait -r 30 -p 3000
# }

# function fetch_ssl_certs {
#   docker-compose exec -T conjur_https cat cert.crt > conjur.pem
# }

# function setup_conjur {
#   docker-compose exec -T conjur_cli bash -c '
#     conjur policy load root /policy/root.yml
#     conjur variable values add ansible/test-secret test_secret_password
#     conjur variable values add ansible/test-secret-in-file test_secret_in_file_password
#     conjur variable values add "ansible/var with spaces" var_with_spaces_secret_password
#   '
# }

# function setup_access_token {
#   docker-compose exec -T conjur_cli bash -c "
#     export CONJUR_AUTHN_LOGIN=host/ansible/ansible-master
#     export CONJUR_AUTHN_API_KEY=\"$ANSIBLE_MASTER_AUTHN_API_KEY\"
#     conjur authn authenticate
#   " > access_token
# }


# function run_test_cases {
#   for test_case in test_cases/*; do
#     run_test_case "$(basename -- "$test_case")"
#   done
# }

# function run_test_case {
#   local test_case=$1
#   echo "---- testing ${test_case} ----"

#   if [ -z "$test_case" ]; then
#     echo ERROR: run_test called with no argument 1>&2
#     exit 1
#   fi

#   docker-compose exec -T ansible bash -exc "
#     cd tests/conjur_variable

#     # If env vars were provided, load them
#     if [ -e 'test_cases/${test_case}/env' ]; then
#       . ./test_cases/${test_case}/env
#     fi

#     # You can add -vvvv here for debugging
#     ansible-playbook 'test_cases/${test_case}/playbook.yml'

#     py.test --junitxml='./junit/${test_case}' \
#       --connection docker \
#       -v 'test_cases/${test_case}/tests/test_default.py'
#   "
# }

# main
