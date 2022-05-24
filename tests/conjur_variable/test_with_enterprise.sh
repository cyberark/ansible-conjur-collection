#!/bin/bash -eu


# normalises project name by filtering non alphanumeric characters and transforming to lowercase
declare -x COMPOSE_PROJECT_NAME
COMPOSE_PROJECT_NAME=$(echo "${BUILD_TAG:-ansible-plugin-testing}-conjur-variable" | sed -e 's/[^[:alnum:]]//g' | tr '[:upper:]' '[:lower:]')
export COMPOSE_PROJECT_NAME

declare -x ANSIBLE_MASTER_AUTHN_API_KEY=''
declare -x CONJUR_ADMIN_AUTHN_API_KEY=''
declare -x ANSIBLE_CONJUR_CERT_FILE=''

function main() {

echo " Step 1"
   pwd
   ls
  pushd ./tests/conjur_variable
  git clone --single-branch --branch main https://github.com/conjurdemos/conjur-intro.git
   # pushd ./conjur-intro
   cd conjur-intro
   echo " Step 2"
    pwd
    ls

    echo " Provision Master"
    ./bin/dap --provision-master
    ./bin/dap --provision-follower

    cp ../policy/root.yml .

    echo " Setup Policy "
    echo " ========load policy====="
    ./bin/cli conjur policy load root root.yml
    echo " ========Set Variable value ansible/test-secret ====="
    ./bin/cli conjur variable values add ansible/test-secret test_secret_password
    echo " =======Set Variable value ansible/test-secret-in-file ====="
    ./bin/cli conjur variable values add ansible/test-secret-in-file test_secret_in_file_password
    echo " =======Set Variable value ansible/var with spaces ====="
    # ./bin/cli conjur variable values add "ansible/var with spaces" var_with_spaces_secret_password

    echo " Setup CLI "
    docker-compose  \
    run \
    --rm \
    -w /src/cli \
    --entrypoint /bin/bash \
    client \
      -c "cp /root/conjur-demo.pem conjur-enterprise.pem"
    cp conjur-enterprise.pem ../

    docker-compose  \
    run \
    --rm \
    -w /src/cli \
    --entrypoint /bin/bash \
    client \
      -c "conjur host rotate_api_key --host ansible/ansible-master
      "> ANSIBLE_MASTER_AUTHN_API_KEY
    cp ANSIBLE_MASTER_AUTHN_API_KEY ../

    echo " Get CONJUR_ADMIN_AUTHN_API_KEY value "
    CONJUR_ADMIN_AUTHN_API_KEY="$(./bin/cli conjur user rotate_api_key|tail -n 1| tr -d '\r')"
    echo "admin api key ANSIBLE_MASTER_AUTHN_API_KEY"
    ANSIBLE_MASTER_AUTHN_API_KEY=$(./bin/cli conjur host rotate_api_key --host ansible/ansible-master)
    echo "ANSIBLE_MASTER_AUTHN_API_KEY: ${ANSIBLE_MASTER_AUTHN_API_KEY}"
    echo "CONJUR_ADMIN_AUTHN_API_KEY: ${CONJUR_ADMIN_AUTHN_API_KEY}"
    echo "${CONJUR_ADMIN_AUTHN_API_KEY}" > api_key
    cp api_key ../
    cd ..
   #    popd

  #   pushd ./tests/conjur_variable

   echo " Step 45 "
    pwd
    ls

    echo " Stage 2 "
    docker build -t conjur_ansible:v1 .
    echo " Run Ansible "

       docker run \
       -d -t \
       --name ansible_container \
       --volume "$(git rev-parse --show-toplevel):/cyberark" \
       --volume "/var/run/docker.sock:/var/run/docker.sock" \
       --network dap_net \
       -e "CONJUR_APPLIANCE_URL=https://conjur-master.mycompany.local" \
       -e "CONJUR_ACCOUNT=cucumber" \
       -e "CONJUR_AUTHN_LOGIN=host/ansible/ansible-master" \
       -e "ANSIBLE_MASTER_AUTHN_API_KEY=${ANSIBLE_MASTER_AUTHN_API_KEY}" \
       -e "ANSIBLE_CONJUR_CERT_FILE=/cyberark/tests/conjur-enterprise.pem" \
       --workdir "/cyberark" \
       conjur_ansible:v1 \

       # --volume "/var/lib/jenkins/workspace/sible-conjur-collection_deleteit/plugins":/root/.ansible/plugins \
       # --volume "${PWD}:/cyberark/tests/conjur_variable" \
       # --volume "${PWD}/conjur-enterprise.pem:/cyberark/tests/conjur-enterprise.pem" \
       # --volume "/var/run/docker.sock:/var/run/docker.sock" \

    docker logs ansible_container
    echo "Running tests"

    run_test_cases
    echo " End of the tests "
  popd
}

function run_test_cases {
  local test_case="retrieve-variable"
    echo "---- testing ${test_case} ----"

  docker exec -t ansible_container bash -exc "
    pwd
    ls
    cd tests
    pwd
    ls
    cd conjur_variable
    pwd
    ls
    # ansible-playbook 'test_cases/${test_case}/playbook.yml'

    # py.test --junitxml='./junit/${test_case}' \
    #   --connection docker \
    #   -v 'test_cases/${test_case}/tests/test_default.py'
  "
}

main