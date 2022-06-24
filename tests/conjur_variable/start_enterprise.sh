#!/bin/bash -eu

# normalises project name by filtering non alphanumeric characters and transforming to lowercase
declare -x COMPOSE_PROJECT_NAME
COMPOSE_PROJECT_NAME=$(echo "${BUILD_TAG:-ansible-plugin-testing}-conjur-variable" | sed -e 's/[^[:alnum:]]//g' | tr '[:upper:]' '[:lower:]')
export COMPOSE_PROJECT_NAME

declare -x ANSIBLE_MASTER_AUTHN_API_KEY=''
declare -x CONJUR_ADMIN_AUTHN_API_KEY=''
declare -x ANSIBLE_CONJUR_CERT_FILE=''

  git submodule update --init --recursive

function main() {

  echo " testing11 "
  pwd
  ls
  pushd ./tests/conjur_variable/conjur-intro

      echo " Provision Master"
      ./bin/dap --provision-master
      ./bin/dap --provision-follower

      echo " Setup Policy "
      echo " ========load policy====="
      pwd
      ls
      cp ../policy/root.yml .
      pwd
      # cp ../tests/conjur_variable/policy/root.yml .

        ./bin/cli conjur policy load root root.yml
        ./bin/cli conjur variable values add ansible/test-secret test_secret_password
        ./bin/cli conjur variable values add ansible/test-secret-in-file test_secret_in_file_password


echo " Testing1 "
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
        conjur variable values add "ansible/var with spaces" var_with_spaces_secret_password
        '

        # conjur variable values add "ansible/var with spaces" var_with_spaces_secret_password
        # conjur policy load root root.yml
        # conjur variable values add ansible/test-secret test_secret_password
        # conjur variable values add ansible/test-secret-in-file test_secret_in_file_password
      echo " Testingtesting "
      pwd
      ls
      cp conjur-enterprise.pem ../.

      # cp conjur-enterprise.pem ../tests/conjur_variable

echo " Testing2 "
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

      echo " Testing45 "

      cp access_token ../.

      # cp access_token ../tests/conjur_variable

      echo " Get CONJUR_ADMIN_AUTHN_API_KEY value "
      CONJUR_ADMIN_AUTHN_API_KEY="$(./bin/cli conjur user rotate_api_key|tail -n 1| tr -d '\r')"
      echo "CONJUR_ADMIN_AUTHN_API_KEY: ${CONJUR_ADMIN_AUTHN_API_KEY}"
  popd

     echo " current pwd "
     pwd
  pushd ./tests/conjur_variable

       echo " Testing4545 "
       pwd
       ls
      #  docker build .
      #  echo " Testing4545451 "
      #  docker build -t conjur_ansible:v2 .
      #  echo " Testing454545 "

      #   -d -t \

       docker run \
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
      #  conjur_ansible:v2

      echo "Running tests"
      run_test_cases
      echo " End of the tests "

      cleanup

  popd

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

function cleanup {
pushd conjur-intro
  docker-compose down -v
popd
}

trap cleanup EXIT
