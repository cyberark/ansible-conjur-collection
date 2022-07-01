#!/bin/bash -eux


# normalises project name by filtering non alphanumeric characters and transforming to lowercase
declare -x COMPOSE_PROJECT_NAME
COMPOSE_PROJECT_NAME=$(echo "${BUILD_TAG:-ansible-plugin-testing}-conjur-variable" | sed -e 's/[^[:alnum:]]//g' | tr '[:upper:]' '[:lower:]')
export COMPOSE_PROJECT_NAME

declare -x ANSIBLE_MASTER_AUTHN_API_KEY=''
declare -x CONJUR_ADMIN_AUTHN_API_KEY=''
declare -x ANSIBLE_CONJUR_CERT_FILE=''

declare -x ansible_cid=''
declare -x cli_cid=''

declare -x access_token=''



function main() {

    git clone --single-branch --branch main https://github.com/conjurdemos/conjur-intro.git

  pushd ./conjur-intro

      docker-compose down -v

      echo " Provision Master"
      ./bin/dap --provision-master
      ./bin/dap --provision-follower

      echo " ========load policy====="
      cp ../tests/conjur_variable/policy/root.yml .
      ./bin/cli conjur policy load root root.yml
      echo " ========Set Variable value ansible/test-secret ====="
      ./bin/cli conjur variable values add ansible/test-secret test_secret_password
      echo " =======Set Variable value ansible/test-secret-in-file ====="
      ./bin/cli conjur variable values add ansible/test-secret-in-file test_secret_in_file_password

      docker-compose  \
      run \
      --rm \
      -w /src/cli \
      --entrypoint /bin/bash \
      client \
        -c "conjur host rotate_api_key --host ansible/ansible-master
      "> ANSIBLE_MASTER_AUTHN_API_KEY

      cp ANSIBLE_MASTER_AUTHN_API_KEY ../
      ANSIBLE_MASTER_AUTHN_API_KEY=$(cat ANSIBLE_MASTER_AUTHN_API_KEY)
      echo "ANSIBLE_MASTER_AUTHN_API_KEY: ${ANSIBLE_MASTER_AUTHN_API_KEY}"

        docker-compose  \
        run \
        --rm \
        -w /src/cli \
        --entrypoint /bin/bash \
        client \
          -ec 'cp /root/conjur-demo.pem conjur-enterprise.pem
          conjur variable values add "ansible/var with spaces" var_with_spaces_secret_password
          '
        cp conjur-enterprise.pem ../tests/conjur_variable

        docker-compose  \
        run \
        --rm \
        -w /src/cli \
        --entrypoint /bin/bash \
        client \
          -c "
              export CONJUR_AUTHN_LOGIN=host/ansible/ansible-master
              export CONJUR_AUTHN_API_KEY=\"$ANSIBLE_MASTER_AUTHN_API_KEY\"
              conjur authn authenticate
            " > access_token
        cp access_token ../tests/conjur_variable

        access_token=$(cat access_token)
        echo "access_token: ${access_token}"

        echo " Get CONJUR_ADMIN_AUTHN_API_KEY value "
        CONJUR_ADMIN_AUTHN_API_KEY="$(./bin/cli conjur user rotate_api_key|tail -n 1| tr -d '\r')"
        echo "CONJUR_ADMIN_AUTHN_API_KEY: ${CONJUR_ADMIN_AUTHN_API_KEY}"

        echo " testing the cli_cid "
        cli_cid=$(docker-compose ps -q client)
        echo "cli_cid value is : ${cli_cid}"
  popd

  pushd ./tests/conjur_variable

       docker build -t conjur_ansible:v1 .
       docker run \
       -d -t \
       --name ansible_container \
       --volume "$(git rev-parse --show-toplevel):/cyberark" \
       --volume "$(git rev-parse --show-toplevel)/plugins":/root/.ansible/plugins \
       --network dap_net \
       -e "CONJUR_APPLIANCE_URL=https://conjur-master.mycompany.local" \
       -e "CONJUR_ACCOUNT=demo" \
       -e "CONJUR_AUTHN_LOGIN=admin" \
       -e "ANSIBLE_MASTER_AUTHN_API_KEY=${ANSIBLE_MASTER_AUTHN_API_KEY}" \
       -e "COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME}" \
       -e "CONJUR_ADMIN_AUTHN_API_KEY=${CONJUR_ADMIN_AUTHN_API_KEY}" \
       -e "ANSIBLE_CONJUR_CERT_FILE=/cyberark/tests/conjur_variable/conjur-enterprise.pem" \
       -e "CONJUR_AUTHN_API_KEY=${CONJUR_ADMIN_AUTHN_API_KEY}" \
       --workdir "/cyberark" \
       conjur_ansible:v1 \

       echo " testing the ansible_cid "
    #    ansible_cid=$(docker-compose ps -q ansible_container)
       ansible_cid=$(docker container ls  | grep 'ansible_container' | awk '{print $1}')
       echo "line 116 ansible_cid value is : ${ansible_cid}"

      echo "Running tests"
      run_test_cases
      echo " End of the tests "
  popd
  pushd ./roles/conjur_host_identity/tests
      echo "Running role test cases"
      run_role_test_cases
      echo " End role test cases"
  popd
  cleanup
}

function run_test_cases {
  for test_case in test_cases/*; do
    run_test_case "$(basename -- "$test_case")"
  done
}
function run_test_case {
  local test_case=$1
  echo "---- testing ${test_case} ----"

  if [ -z "$test_case" ]; then
    echo ERROR: run_test called with no argument 1>&2
    exit 1
  fi

  docker exec -t ansible_container bash -exc "
    cd tests/conjur_variable

    # If env vars were provided, load them
    if [ -e 'test_cases/${test_case}/env_enterprise' ]; then
      . ./test_cases/${test_case}/env_enterprise
    fi

    # You can add -vvvv here for debugging
    ansible-playbook 'test_cases/${test_case}/playbook.yml'

    # py.test --junitxml='./junit/${test_case}' \
    #   --connection docker \
    #   -v 'test_cases/${test_case}/tests/test_default.py'
  "
}

main


function run_role_test_cases {
  for test_case in test_cases/*; do
    teardown_and_setup
    run_test_case "$(basename -- "$test_case")"
  done
}

function run_role_test_case {
  echo "---- testing ${test_case} ----"
  local test_case=$1
  if [ -n "$test_case" ]
  then
    docker exec "${ansible_cid}" env HFTOKEN="$(hf_token)" bash -ec "
      cd tests
      ansible-playbook test_cases/${test_case}/playbook.yml
    "
    if [ "${test_case}" == "configure-conjur-identity" ]
    then
          docker exec "${ansible_cid}" bash -ec "
            cd tests
            py.test --junitxml=./junit/${test_case} --connection docker -v test_cases/${test_case}/tests/test_default.py
          "
    fi
  else
    echo ERROR: run_test called with no argument 1>&2
    exit 1
  fi
}

function hf_token {
  docker exec "${cli_cid}" bash -c "conjur hostfactory tokens create --duration-days=5 ansible/ansible-factory | jq -r '.[0].token'"
}

function teardown_and_setup {
  docker-compose up -d --force-recreate --scale test_app_ubuntu=2 test_app_ubuntu
  docker-compose up -d --force-recreate --scale test_app_centos=2 test_app_centos
}

function cleanup {
pushd conjur-intro
  docker-compose down -v
popd
}


trap cleanup EXIT
