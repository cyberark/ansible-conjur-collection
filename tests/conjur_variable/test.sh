#!/bin/bash -eu

set -o pipefail

# normalises project name by filtering non alphanumeric characters and transforming to lowercase
declare -x COMPOSE_PROJECT_NAME=''
declare -x ENTERPRISE_PROJECT='conjur-intro-variable'
declare -x ANSIBLE_PROJECT=''

declare -x ANSIBLE_MASTER_AUTHN_API_KEY=''
declare -x CONJUR_ADMIN_AUTHN_API_KEY=''
declare -x DOCKER_NETWORK="default"
declare -x ANSIBLE_VERSION="${ANSIBLE_VERSION:-6}"

ANSIBLE_PROJECT=$(echo "${BUILD_TAG:-ansible-plugin-testing}-conjur-variable" | sed -e 's/[^[:alnum:]]//g' | tr '[:upper:]' '[:lower:]')

enterprise="false"
cli_cid=""
test_dir="$(pwd)"

function cleanup {
  echo 'Removing test environment'
  echo '---'

  # Escape conjur-intro dir if Enterprise setup fails
  cd "${test_dir}"

  if [[ -d conjur-intro ]]; then
    pushd conjur-intro
      COMPOSE_PROJECT_NAME="${ENTERPRISE_PROJECT}"
      ./bin/dap --stop
    popd
    rm -rf conjur-intro
  fi

  COMPOSE_PROJECT_NAME="${ANSIBLE_PROJECT}"
  docker-compose down -v
  rm -f conjur.pem \
        access_token
}
trap cleanup EXIT

while getopts 'e' flag; do
  case "${flag}" in
    e) enterprise="true" ;;
    *) exit 1 ;;
   esac
done

cleanup

function wait_for_conjur {
  echo "Waiting for Conjur server to come up"
  docker-compose exec -T conjur conjurctl wait -r 30 -p 3000
}

function fetch_ssl_certs {
  echo "Fetching SSL certs"
  service_id="conjur_https"
  cert_path="cert.crt"
  if [[ "${enterprise}" == "true" ]]; then
    service_id="conjur-master.mycompany.local"
    cert_path="/etc/ssl/certs/ca.pem"
  fi

  (docker-compose exec -T "${service_id}" cat "${cert_path}") > conjur.pem
}

function setup_conjur_resources {
  echo "Configuring Conjur via CLI"

  policy_path="root.yml"
  if [[ "${enterprise}" == "false" ]]; then
    policy_path="/policy/${policy_path}"
  fi

  docker exec "${cli_cid}" bash -c "
    conjur policy load root ${policy_path}
    conjur variable values add ansible/test-secret test_secret_password
    conjur variable values add ansible/test-secret-in-file test_secret_in_file_password
    conjur variable values add 'ansible/var with spaces' var_with_spaces_secret_password
  "
}

function setup_admin_api_key {
  echo "Fetching admin API key"
  if [[ "$enterprise" == "true" ]]; then
    CONJUR_ADMIN_AUTHN_API_KEY="$(docker exec "${cli_cid}" conjur user rotate_api_key)"
  else
    CONJUR_ADMIN_AUTHN_API_KEY="$(docker-compose exec -T conjur conjurctl role retrieve-key "${CONJUR_ACCOUNT}":user:admin)"
  fi
}

function setup_ansible_api_key {
  echo "Fetching Ansible master host credentials"
  ANSIBLE_MASTER_AUTHN_API_KEY="$(docker exec "${cli_cid}" conjur host rotate_api_key --host ansible/ansible-master)"
}

function setup_access_token {
  echo "Get Access Token"
  docker exec "${cli_cid}" bash -c "
    export CONJUR_AUTHN_LOGIN=host/ansible/ansible-master
    export CONJUR_AUTHN_API_KEY=\"$ANSIBLE_MASTER_AUTHN_API_KEY\"
    conjur authn authenticate
  " > access_token
}

function setup_conjur_open_source()  {
  docker-compose up -d --build conjur \
                               conjur_https

  wait_for_conjur
  fetch_ssl_certs
  setup_admin_api_key

  echo "Creating Conjur CLI with admin credentials"
  docker-compose up -d conjur_cli
  cli_cid="$(docker-compose ps -q conjur_cli)"

  setup_conjur_resources
  setup_ansible_api_key
  setup_access_token
}

function setup_conjur_enterprise() {
  git clone --single-branch --branch main https://github.com/conjurdemos/conjur-intro.git
  pushd ./conjur-intro

    echo "Provisioning Enterprise leader and follower"
    ./bin/dap --provision-master
    ./bin/dap --provision-follower

    cp ../policy/root.yml .

    # Run 'sleep infinity' in the CLI container, so the scripts
    # have access to an alive and authenticated CLI until the script terminates
    cli_cid="$(docker-compose run -d \
      -w /src/cli \
      --entrypoint sleep client infinity)"

    echo "Authenticate Conjur CLI container"
    docker exec "${cli_cid}" \
      /bin/bash -c "
        if [ ! -e /root/conjur-demo.pem ]; then
          yes 'yes' | conjur init -u ${CONJUR_APPLIANCE_URL} -a ${CONJUR_ACCOUNT}
        fi
        conjur authn login -u admin -p MySecretP@ss1
        hostname -I
      "

    fetch_ssl_certs
    setup_conjur_resources
    setup_admin_api_key
    setup_ansible_api_key
    setup_access_token

    echo "Relocate credential files"
    mv conjur.pem ../.
    mv access_token ../.
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

function main() {
  if [[ "$enterprise" == "true" ]]; then
    echo "Deploying Conjur Enterprise"

    export CONJUR_APPLIANCE_URL="https://conjur-master.mycompany.local"
    export CONJUR_ACCOUNT="demo"
    COMPOSE_PROJECT_NAME="${ENTERPRISE_PROJECT}"
    DOCKER_NETWORK="dap_net"

    setup_conjur_enterprise
  else
    echo "Deploying Conjur Open Source"

    export CONJUR_APPLIANCE_URL="https://conjur-https"
    export CONJUR_ACCOUNT="cucumber"
    COMPOSE_PROJECT_NAME="${ANSIBLE_PROJECT}"

    setup_conjur_open_source
  fi

  COMPOSE_PROJECT_NAME="${ANSIBLE_PROJECT}"
  export CONJUR_AUTHN_LOGIN="host/ansible/ansible-master"

  echo "Preparing Ansible for test run"
  docker-compose up -d --build ansible

  echo "Running tests"
  run_test_cases
}

main
