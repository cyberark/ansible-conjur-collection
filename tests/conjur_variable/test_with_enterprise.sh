#!/bin/bash -eu


# normalises project name by filtering non alphanumeric characters and transforming to lowercase
declare -x COMPOSE_PROJECT_NAME
COMPOSE_PROJECT_NAME=$(echo "${BUILD_TAG:-ansible-plugin-testing}-conjur-variable" | sed -e 's/[^[:alnum:]]//g' | tr '[:upper:]' '[:lower:]')
export COMPOSE_PROJECT_NAME

declare -x ANSIBLE_MASTER_AUTHN_API_KEY=''
declare -x CONJUR_ADMIN_AUTHN_API_KEY=''
declare -x ANSIBLE_CONJUR_CERT_FILE=''

function main() {

      echo " stage 1"
      pwd
      ls
    git clone --single-branch --branch main https://github.com/conjurdemos/conjur-intro.git
    # pushd ./conjur-intro
    cd conjur-intro
      echo " stage 2"
      pwd
      ls
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

# echo " Setup CLI "
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
  # cp ANSIBLE_MASTER_AUTHN_API_KEY ../tests/conjur_variable

  echo " Get CONJUR_ADMIN_AUTHN_API_KEY value "
  CONJUR_ADMIN_AUTHN_API_KEY="$(./bin/cli conjur user rotate_api_key|tail -n 1| tr -d '\r')"
  echo "admin api key: ${CONJUR_ADMIN_AUTHN_API_KEY}"
  api_key=$CONJUR_ADMIN_AUTHN_API_KEY
  echo "${CONJUR_ADMIN_AUTHN_API_KEY}" > api_key
  cp api_key ../
    echo " stage 3"
    pwd
    ls
  cd ..
    echo " stage 4"
    pwd
    ls
  # popd
  cd tests/conjur_variable
    echo " stage 5"
    pwd
    ls
  # echo "Waiting for Conjur server to come up"
  # wait_for_conjur

  echo "Fetching SSL certs"
  fetch_ssl_certs

  echo "Fetching admin API key"
  # CONJUR_ADMIN_AUTHN_API_KEY=$(docker-compose exec -T conjur conjurctl role retrieve-key cucumber:user:admin)

  # echo "Fetching Ansible master host credentials"
  # ANSIBLE_MASTER_AUTHN_API_KEY=$(docker-compose exec -T conjur_cli conjur host rotate_api_key --host ansible/ansible-master)
  ANSIBLE_CONJUR_CERT_FILE='/cyberark/tests/conjur-enterprise.pem'

  # echo "Preparing Ansible for test run"
    docker-compose up -d --build ansible

    docker-compose run \
    --volume "${PWD}/ANSIBLE_MASTER_AUTHN_API_KEY:/ANSIBLE_MASTER_AUTHN_API_KEY" \
    --volume "${PWD}/conjur-enterprise.pem:/cyberark/tests/conjur-enterprise.pem" \
    --volume "../../plugins:/root/.ansible/plugins" \
    --volume "../..:/cyberark" \
    --volume "/var/run/docker.sock:/var/run/docker.sock" \
    --network dap_net \
    -e "CONJUR_APPLIANCE_URL=https://conjur-master.mycompany.local" \
    -e "CONJUR_ACCOUNT=demo" \
    -e "CONJUR_AUTHN_LOGIN=admin" \
    -e "CONJUR_ADMIN_AUTHN_API_KEY=${CONJUR_ADMIN_AUTHN_API_KEY}" \
    -e "ANSIBLE_CONJUR_CERT_FILE=/cyberark/tests/conjur-enterprise.pem" \
    --workdir "/cyberark" \
    --rm \
    --no-deps \
    --entrypoint /bin/bash \
    ansible \
  #   "${COMPOSE_PROJECT_NAME}"-ansible

    echo "Running tests"
    run_test_cases
    echo " End of the tests "
}

function fetch_ssl_certs {
 echo "Running fetch_ssl_certs"
 docker-compose up -d --build conjur_https
 docker-compose exec -T conjur_https cat cert.crt > conjur.pem
}

function setup_access_token {
  docker-compose exec -T client bash -c "
    export CONJUR_AUTHN_LOGIN=host/ansible/ansible-master
    export CONJUR_AUTHN_API_KEY=\"$ANSIBLE_MASTER_AUTHN_API_KEY\"
    conjur authn authenticate
  " > access_token
}

  # retrieve-variable-bad-cert-path NoError
  # retrieve-variable-bad-certs NoError
  # retrieve-variable-into-file NoError
  # retrieve-variable Error

function run_test_cases {
  local test_case="retrieve-variable"
  echo "---- testing ${test_case} ----"

  docker-compose exec -T ansible bash -exc "
    cd tests/conjur_variable

    # if [ -e 'test_cases/${test_case}/env' ]; then
    #   . ./test_cases/${test_case}/env
    # fi

    # You can add -vvvv here for debugging
    ansible-playbook 'test_cases/${test_case}/playbook.yml'
    py.test --junitxml='./junit/${test_case}' \
      --connection docker \
      -v 'test_cases/${test_case}/tests/test_default.py'
  "
}

main
