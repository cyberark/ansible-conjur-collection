#!/bin/bash -eu


# normalises project name by filtering non alphanumeric characters and transforming to lowercase
declare -x COMPOSE_PROJECT_NAME
COMPOSE_PROJECT_NAME=$(echo "${BUILD_TAG:-ansible-plugin-testing}-conjur-variable" | sed -e 's/[^[:alnum:]]//g' | tr '[:upper:]' '[:lower:]')
export COMPOSE_PROJECT_NAME

declare -x ANSIBLE_MASTER_AUTHN_API_KEY=''
declare -x CONJUR_ADMIN_AUTHN_API_KEY=''
declare -x ANSIBLE_CONJUR_CERT_FILE=''

function main() {

  git clone --single-branch --branch main https://github.com/conjurdemos/conjur-intro.git
  pushd ./conjur-intro

    echo " Provision Master"
    ./bin/dap --provision-master
    ./bin/dap --provision-follower

    cp ../tests/conjur_variable/policy/root.yml .

    echo " Setup Policy "
    echo " ========load policy====="
    ./bin/cli conjur policy load root root.yml
    echo " ========Set Variable value ansible/test-secret ====="
    ./bin/cli conjur variable values add ansible/test-secret test_secret_password
    echo " =======Set Variable value ansible/test-secret-in-file ====="
    ./bin/cli conjur variable values add ansible/test-secret-in-file test_secret_in_file_password
    echo " =======Set Variable value ansible/var with spaces ====="
    # ./bin/cli conjur variable values add "ansible/var with spaces" var_with_spaces_secret_password



    docker-compose  \
    run \
    --rm \
    -w /src/cli \
    --entrypoint /bin/bash \
    client \
      -c "conjur host rotate_api_key --host ansible/ansible-master
     "> ANSIBLE_MASTER_AUTHN_API_KEY
    cp ANSIBLE_MASTER_AUTHN_API_KEY ../

    echo " ====== testing 1 ======= "
    ANSIBLE_MASTER_AUTHN_API_KEY=$(cat ANSIBLE_MASTER_AUTHN_API_KEY)
    echo "$ANSIBLE_MASTER_AUTHN_API_KEY"
    pwd
    ls
    echo " ===== testing 2 ========"

    # echo " Setup CLI "
    docker-compose  \
    run \
    --rm \
    -e "CONJUR_AUTHN_LOGIN=host/ansible/ansible-master" \
    -e "CONJUR_AUTHN_API_KEY=${ANSIBLE_MASTER_AUTHN_API_KEY}" \
    -w /src/cli \
    --entrypoint /bin/bash \
    client \
      -c "cp /root/conjur-demo.pem conjur-enterprise.pem
      conjur authn authenticate
      "
    cp conjur-enterprise.pem ../

    echo " Get CONJUR_ADMIN_AUTHN_API_KEY value "
    CONJUR_ADMIN_AUTHN_API_KEY="$(./bin/cli conjur user rotate_api_key|tail -n 1| tr -d '\r')"
    echo "admin api key: ${CONJUR_ADMIN_AUTHN_API_KEY}"
    echo "${CONJUR_ADMIN_AUTHN_API_KEY}" > api_key
    cp api_key ../
  popd

  pushd ./tests/conjur_variable

    docker build -t conjur_ansible:v1 .
    echo " Stage 2 "
    docker ps
    docker images

    pwd
    ls
    echo " Run Ansible "

       docker run \
       -d -t \
       --name ansible_container \
       --volume "/var/lib/jenkins/workspace/ection_test_15266_addedTestCases:/cyberark" \
       --volume "/var/lib/jenkins/workspace/ection_test_15266_addedTestCases/plugins":/root/.ansible/plugins \
       --volume "${PWD}/conjur-enterprise.pem:/cyberark/tests/conjur-enterprise.pem" \
       --volume "${PWD}/conjur-enterprise.pem:/cyberark/tests/conjur_variable/conjur-enterprise.pem" \
       --volume "/var/run/docker.sock:/var/run/docker.sock" \
       --network dap_net \
       -e "CONJUR_APPLIANCE_URL=https://conjur-master.mycompany.local" \
       -e "CONJUR_ACCOUNT=demo" \
       -e "CONJUR_AUTHN_LOGIN=admin" \
       -e "CONJUR_ADMIN_AUTHN_API_KEY=${CONJUR_ADMIN_AUTHN_API_KEY}" \
       -e "ANSIBLE_MASTER_AUTHN_API_KEY=${ANSIBLE_MASTER_AUTHN_API_KEY}" \
       -e "ANSIBLE_CONJUR_CERT_FILE=/cyberark/tests/conjur-enterprise.pem" \
       --workdir "/cyberark" \
       conjur_ansible:v1 \

       #  Note : ANSIBLE_CONJUR_CERT_FILE path need to correct

       echo " Ansible logs "
       docker logs ansible_container

        echo " Ansible inspect "
       docker inspect ansible_container

    echo "Running tests"
    docker ps
    docker images

    run_test_cases
    echo " End of the tests "
  popd
}

function run_test_cases {
  local test_case="retrieve-variable"
  echo "---- Run test cases ----"
  docker exec -t ansible_container bash -exc "
   cd tests/conjur_variable
   ansible-playbook 'test_cases/${test_case}/playbook.yml'

    # py.test --junitxml='./junit/${test_case}' \
    #   --connection docker \
    #   -v 'test_cases/${test_case}/tests/test_default.py'
  "
}

main
