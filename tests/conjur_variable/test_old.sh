#!/bin/bash -e

set -o pipefail

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

enterprise="true"
cli_service="client"

function main()
{
  if [[ "$enterprise" == "true" ]]; then
            echo "Deploying Conjur Enterprise"

            export DOCKER_NETWORK="dap_net"
            export CONJUR_APPLIANCE_URL="https://conjur-master.mycompany.local"
            export CONJUR_ACCOUNT="demo"
            export ANSIBLE_CONJUR_CERT_FILE="/cyberark/tests/conjur-enterprise.pem"
            export CONJUR_AUTHN_LOGIN="admin"
            export ANSIBLE_CONJUR_CERT_FILE="/cyberark/tests/conjur_variable/conjur-enterprise.pem"

            export ANSIBLE_ROOT=":/cyberark"

            ANSIBLE_PLUGIN=""'/plugins'""

            export ANSIBLE_PLUGIN
            export ANSIBLE_PLUGIN_PATH=":/root/.ansible/plugins"
            conjur_variable_test_path=$(git rev-parse --show-toplevel)$ANSIBLE_ROOT
            conjur_variable_test_plugins=$(git rev-parse --show-toplevel)$ANSIBLE_PLUGIN$ANSIBLE_PLUGIN_PATH

            echo "it is conjur_variable_test_path ${conjur_variable_test_path}"
            echo "it is conjur_variable_test_plugins ${conjur_variable_test_plugins}"

            export conjur_variable_test_plugins
            export conjur_variable_test_path

            echo " $conjur_variable_test_path "
            setup_conjur_enterprise
  else
            echo "Deploying Conjur Open Source"

            export CONJUR_APPLIANCE_URL="https://conjur-https"
            export CONJUR_ACCOUNT="cucumber"
            export ANSIBLE_CONJUR_CERT_FILE="/cyberark/tests/conjur.pem"

            setup_conjur_open_source
  fi
}

function setup_conjur_open_source() {
  docker-compose up -d --build conjur \
                               conjur_https \
                               conjur_cli \

  echo "Waiting for Conjur server to come up"
  wait_for_conjur

  echo "Fetching SSL certs"
  fetch_ssl_certs

  echo "Fetching admin API key"
  CONJUR_ADMIN_AUTHN_API_KEY=$(docker-compose exec -T conjur conjurctl role retrieve-key cucumber:user:admin)

  echo "Recreating conjur CLI with admin credentials"
  docker-compose up -d conjur_cli

  echo "Configuring Conjur via CLI"
  setup_conjur

  echo "Fetching Ansible master host credentials"
  ANSIBLE_MASTER_AUTHN_API_KEY=$(docker-compose exec -T conjur_cli conjur host rotate_api_key --host ansible/ansible-master)
  ANSIBLE_CONJUR_CERT_FILE='/cyberark/tests/conjur.pem'

  echo "Get Access Token"
  setup_access_token

  echo "Preparing Ansible for test run"
  docker-compose up -d --build ansible

  echo "Running tests"
  run_test_cases
}

function wait_for_conjur {
  docker-compose exec -T conjur conjurctl wait -r 30 -p 3000
}

function fetch_ssl_certs {
  docker-compose exec -T conjur_https cat cert.crt > conjur.pem
}

function setup_conjur {
  docker-compose exec -T conjur_cli bash -c '
    conjur policy load root /policy/root.yml
    conjur variable values add ansible/test-secret test_secret_password
    conjur variable values add ansible/test-secret-in-file test_secret_in_file_password
    conjur variable values add "ansible/var with spaces" var_with_spaces_secret_password
  '
}

function setup_access_token {
  docker-compose exec -T conjur_cli bash -c "
    export CONJUR_AUTHN_LOGIN=host/ansible/ansible-master
    export CONJUR_AUTHN_API_KEY=\"$ANSIBLE_MASTER_AUTHN_API_KEY\"
    conjur authn authenticate
  " > access_token
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

  docker-compose exec -T ansible bash -exc "
    cd tests/conjur_variable

    # If env vars were provided, load them
    if [ -e 'test_cases/${test_case}/env' ]; then
      . ./test_cases/${test_case}/env
    fi

    # You can add -vvvv here for debugging
    ansible-playbook 'test_cases/${test_case}/playbook.yml'

    py.test --junitxml='./junit/${test_case}' \
      --connection docker \
      -v 'test_cases/${test_case}/tests/test_default.py'
  "
}

#  ====== common start =======

    function setup_conjur_resources {
    echo "Configuring Conjur via CLI"

    policy_path="root.yml"
    if [[ "${enterprise}" == "false" ]]; then
        policy_path="/policy/${policy_path}"
    fi

    echo " test enterprise value ${enterprise} "
    echo " test  value ${enterprise} "


    docker-compose exec -T "${cli_service}" bash -c "
        conjur policy load root ${policy_path}
        conjur variable values add ansible/test-secret test_secret_password
        conjur variable values add ansible/test-secret-in-file test_secret_in_file_password
        conjur variable values add "ansible/var with spaces" var_with_spaces_secret_password
    "
    }

    function setup_admin_api_key {
    echo "Fetching admin API key"
    if [[ "$enterprise" == "true" ]]; then
        CONJUR_ADMIN_AUTHN_API_KEY="$(docker-compose exec -T ${cli_service} conjur user rotate_api_key)"
    else
        CONJUR_ADMIN_AUTHN_API_KEY="$(docker-compose exec -T conjur conjurctl role retrieve-key ${CONJUR_ACCOUNT}:user:admin)"
    fi
    }

    function fetch_ssl_certs {
    echo "Fetching SSL certs"
    if [[ "${enterprise}" == "true" ]]; then
        docker-compose exec -T "${cli_service}" cat /root/conjur-demo.pem > conjur-enterprise.pem
    else
        docker-compose exec -T conjur_https cat cert.crt > conjur.pem
    fi
    }

#  =======  Common end =======


# ======== Enterprise Start =============

function setup_conjur_enterprise() {

    git clone --single-branch --branch main https://github.com/conjurdemos/conjur-intro.git

  pushd ./conjur-intro

      docker-compose down -v

      echo " Provision Master"
      ./bin/dap --provision-master
      ./bin/dap --provision-follower

      echo " ========load policy====="
      cp ../tests/conjur_variable/policy/root.yml .

      setup_conjur_resources

    #   ./bin/cli conjur policy load root root.yml
    #   echo " ========Set Variable value ansible/test-secret ====="
    #   ./bin/cli conjur variable values add ansible/test-secret test_secret_password
    #   echo " =======Set Variable value ansible/test-secret-in-file ====="
    #   ./bin/cli conjur variable values add ansible/test-secret-in-file test_secret_in_file_password

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

        fetch_ssl_certs

        # docker-compose  \
        # run \
        # --rm \
        # -w /src/cli \
        # --entrypoint /bin/bash \
        # client \
        #   -ec 'cp /root/conjur-demo.pem conjur-enterprise.pem
        #   conjur variable values add "ansible/var with spaces" var_with_spaces_secret_password
        #   '
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
        setup_admin_api_key
        # CONJUR_ADMIN_AUTHN_API_KEY="$(./bin/cli conjur user rotate_api_key|tail -n 1| tr -d '\r')"
        echo "CONJUR_ADMIN_AUTHN_API_KEY: ${CONJUR_ADMIN_AUTHN_API_KEY}"
  popd

  pushd ./tests/conjur_variable

       docker build -t conjur_ansible:v1 .

       docker run \
       -d -t \
       --name ansible_container \
       --volume "${conjur_variable_test_path}" \
       --volume "${conjur_variable_test_plugins}" \
       --network "${DOCKER_NETWORK}" \
       -e "CONJUR_APPLIANCE_URL=${CONJUR_APPLIANCE_URL}" \
       -e "CONJUR_ACCOUNT=${CONJUR_ACCOUNT}" \
       -e "CONJUR_AUTHN_LOGIN=${CONJUR_AUTHN_LOGIN}" \
       -e "ANSIBLE_MASTER_AUTHN_API_KEY=${ANSIBLE_MASTER_AUTHN_API_KEY}" \
       -e "COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME}" \
       -e "CONJUR_ADMIN_AUTHN_API_KEY=${CONJUR_ADMIN_AUTHN_API_KEY}" \
       -e "ANSIBLE_CONJUR_CERT_FILE=${ANSIBLE_CONJUR_CERT_FILE}" \
       -e "CONJUR_AUTHN_API_KEY=${CONJUR_ADMIN_AUTHN_API_KEY}" \
       --workdir "/cyberark" \
       conjur_ansible:v1 \

      echo "Running tests"
      run_test_cases
      echo " End of the tests "
  popd

#   cleanup
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

  env_file="env"
  if [[ "$enterprise" == "true" ]]; then
    env_file="env_enterprise"
  fi

  docker-compose exec -T ansible bash -exc "
    cd tests/conjur_variable

    # If env vars were provided, load them
    if [ -e 'test_cases/${test_case}/${env_file}' ]; then
      . ./test_cases/${test_case}/${env_file}
    fi

    # You can add -vvvv here for debugging
    ansible-playbook 'test_cases/${test_case}/playbook.yml'

  "
}

# =========== Enterprise End ============
main
