#!/bin/bash -eu


# normalises project name by filtering non alphanumeric characters and transforming to lowercase
declare -x COMPOSE_PROJECT_NAME
COMPOSE_PROJECT_NAME=$(echo "${BUILD_TAG:-ansible-plugin-testing}-conjur-variable" | sed -e 's/[^[:alnum:]]//g' | tr '[:upper:]' '[:lower:]')
export COMPOSE_PROJECT_NAME

declare -x ANSIBLE_MASTER_AUTHN_API_KEY=''
declare -x CONJUR_ADMIN_AUTHN_API_KEY=''
declare -x ANSIBLE_CONJUR_CERT_FILE=''
declare -x containerid=''

# function cleanup {
# pushd conjur-intro
#   docker-compose down -v
# popd
# }

# trap cleanup EXIT

function main() {

echo "get current directory"

        git clone --single-branch --branch main https://github.com/conjurdemos/conjur-intro.git

        pushd ./conjur-intro

            docker-compose down -v

            echo " Provision Master"
            ./bin/dap --provision-master
            ./bin/dap --provision-follower

            echo " Setup Policy "
            pwd
            ls

            cp ../roles/conjur_host_identity/tests/policy/root.yml .
            ./bin/cli conjur policy load root root.yml
            echo " ========Set Variable value ansible/test-secret ====="
            ./bin/cli conjur variable values add ansible/target-password target_secret_password
            # ./bin/cli conjur variable values add ansible/test-secret test_secret_password
            echo " =======Set Variable value ansible/test-secret-in-file ====="
            # ./bin/cli conjur variable values add ansible/test-secret-in-file test_secret_in_file_password

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

            echo " Setup CLI "
                docker-compose  \
                run \
                --rm \
                -w /src/cli \
                --entrypoint /bin/bash \
                client \
                -ec 'cp /root/conjur-demo.pem conjur-enterprise.pem
                '

                echo " ========testit 1====="
                pwd
                ls
                cp conjur-enterprise.pem ../.

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

                echo " ========testit 2====="
                pwd
                ls
                cp access_token ../.

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

            echo "testing purpose only"
            pwd
            ls

        pushd ./roles/conjur_host_identity/tests
            echo " ========testit 3====="
            docker build -t conjur_ansible:v1 .
            echo " ========testit 4====="
            docker run \
            -d -t \
            --name ansible_container \
            --volume "$(git rev-parse --show-toplevel)/roles/conjur_host_identity/tests:/cyberark/tests" \
            --volume "$(git rev-parse --show-toplevel)/roles/conjur_host_identity":/cyberark/cyberark.conjur.conjur-host-identity \
            --network dap_net \
            -e "CONJUR_APPLIANCE_URL=https://conjur-master.mycompany.local" \
            -e "CONJUR_ACCOUNT=demo" \
            -e "CONJUR_AUTHN_LOGIN=admin" \
            -e "ANSIBLE_MASTER_AUTHN_API_KEY=${ANSIBLE_MASTER_AUTHN_API_KEY}" \
            -e "COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME}" \
            -e "ANSIBLE_CONJUR_CERT_FILE=/cyberark/tests/conjur-enterprise.pem" \
            -e "CONJUR_AUTHN_API_KEY=${CONJUR_ADMIN_AUTHN_API_KEY}" \
            --workdir "/cyberark" \
            conjur_ansible:v1 \

              #   -e "ANSIBLE_CONJUR_CERT_FILE=/cyberark/tests/conjur_variable/conjur-enterprise.pem" \

              #   -e "CONJUR_ADMIN_AUTHN_API_KEY=${CONJUR_ADMIN_AUTHN_API_KEY}" \

              echo "Running tests"
              containerid=$(docker ps -aqf "name=ansible_container")
              echo " container Id 1 is ${containerid} "
              run_test_cases
              echo " End of the tests "

        popd

   # cleanup
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