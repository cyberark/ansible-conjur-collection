#!/bin/bash -eu

# normalises project name by filtering non alphanumeric characters and transforming to lowercase
declare -x COMPOSE_PROJECT_NAME
COMPOSE_PROJECT_NAME=$(echo "${BUILD_TAG:-ansible-plugin-testing}-conjur-variable" | sed -e 's/[^[:alnum:]]//g' | tr '[:upper:]' '[:lower:]')
export COMPOSE_PROJECT_NAME

declare -x hf_token=''

function main() {

echo "get current directory"

        git clone --single-branch --branch main https://github.com/conjurdemos/conjur-intro.git

        pushd ./conjur-intro

            docker-compose down -v

            echo " Provision Master"
            ./bin/dap --provision-master
            ./bin/dap --provision-follower

            cp ../roles/conjur_host_identity/tests/policy/root.yml .
            ./bin/cli conjur policy load root root.yml
            echo " ========Set Variable value ansible/test-secret ====="
            ./bin/cli conjur variable values add ansible/target-password target_secret_password

            echo " Get hf_token value "
            docker-compose  \
            run \
            --rm \
            -w /src/cli \
            --entrypoint /bin/bash \
            client \
                -c "conjur hostfactory tokens create --duration-days=5 ansible/ansible-factory | jq -r '.[0].token'"> hf_token

            cp hf_token ../
            hf_token=$(cat hf_token)
            echo "hf_token: ${hf_token}"

            echo " Get CONJUR_ADMIN_AUTHN_API_KEY value "
            CONJUR_ADMIN_AUTHN_API_KEY="$(./bin/cli conjur user rotate_api_key|tail -n 1| tr -d '\r')"
            echo "CONJUR_ADMIN_AUTHN_API_KEY: ${CONJUR_ADMIN_AUTHN_API_KEY}"
        popd

        pushd ./roles/conjur_host_identity/tests
            echo " ========testit 3====="
            ls
            docker build -t conjur_ansible:v1 .
            echo " ========testit 4====="

            role_path="roles/conjur_host_identity"
            role_test_path="roles/conjur_host_identity/tests"

            ansible_role_path="cyberark/cyberark.conjur.conjur-host-identity"
            ansible_tests_path="cyberark/tests"

            CONJUR_APPLIANCE_URL="https://conjur-master.mycompany.local"
            CONJUR_ACCOUNT="demo"
            CONJUR_AUTHN_LOGIN="admin"
            ANSIBLE_CONJUR_CERT_FILE="/cyberark/tests/conjur-enterprise.pem"

            docker run \
            -d -t \
            --name ansible_container \
            --volume "$(git rev-parse --show-toplevel)/${role_test_path}:/${ansible_tests_path}" \
            --volume "$(git rev-parse --show-toplevel)/${role_path}:/${ansible_role_path}" \
            --network dap_net \
            -e "CONJUR_APPLIANCE_URL=${CONJUR_APPLIANCE_URL}" \
            -e "CONJUR_ACCOUNT=${CONJUR_ACCOUNT}" \
            -e "CONJUR_AUTHN_LOGIN=${CONJUR_AUTHN_LOGIN}" \
            -e "COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME}" \
            -e "ANSIBLE_CONJUR_CERT_FILE=${ANSIBLE_CONJUR_CERT_FILE}" \
            -e "CONJUR_AUTHN_API_KEY=${CONJUR_ADMIN_AUTHN_API_KEY}" \
            --workdir "/cyberark" \
            conjur_ansible:v1 \

              echo "Running tests"
              containerid=$(docker ps -aqf "name=ansible_container")
              echo " container Id 1 is ${containerid} "
              run_test_cases
              echo " End of the tests "

        popd
}

function run_test_cases {
  for test_case in test_cases/*; do
    teardown_and_setup
    run_test_case "$(basename -- "$test_case")"
  done
}

function run_test_case {
  echo "---- testing ${test_case} ----"
  local test_case=$1
  if [ -n "$test_case" ]
  then
    docker exec -t ansible_container env HFTOKEN="${hf_token}" bash -exc "
      cd tests
      ansible-playbook test_cases/${test_case}/playbook.yml
    "
    # if [ "${test_case}" == "configure-conjur-identity" ]
    # then
    # echo "---- testing 99 --"
    #       docker exec -t ansible_container bash -exc "
    #         cd tests
    #         py.test --junitxml=./junit/${test_case} --connection docker -v test_cases/${test_case}/tests/test_default.py
    #       "
    # fi
  else
    echo ERROR: run_test called with no argument 1>&2
    exit 1
  fi
}

function teardown_and_setup {
  docker-compose up -d --force-recreate --scale test_app_ubuntu=2 test_app_ubuntu
  docker-compose up -d --force-recreate --scale test_app_centos=2 test_app_centos
}

main

function cleanup {
pushd ./conjur-intro
  docker-compose down -v
popd
}

trap cleanup EXIT