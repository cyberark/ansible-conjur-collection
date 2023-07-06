#!/bin/bash -eu

set -o pipefail

# normalises project name by filtering non alphanumeric characters and transforming to lowercase
declare -x COMPOSE_PROJECT_NAME=''
declare -x ENTERPRISE_PROJECT='conjur-intro-host'
declare -x ANSIBLE_PROJECT=''

declare -x ANSIBLE_CONJUR_AUTHN_API_KEY=''
declare -x CLI_CONJUR_AUTHN_API_KEY=''
declare -x DOCKER_NETWORK="default"
declare -x ANSIBLE_VERSION="${ANSIBLE_VERSION:-6}"

declare cli_cid=''
declare ansible_cid=''
declare enterprise='true'
declare test_dir=''

  ANSIBLE_PROJECT=$(echo "${BUILD_TAG:-ansible-plugin-testing}-conjur-host-identity" | sed -e 's/[^[:alnum:]]//g' | tr '[:upper:]' '[:lower:]')
  test_dir="$(pwd)"

function clean {
  echo 'Removing test environment'

  # Escape conjur-intro dir if Enterprise setup fails
  cd "${test_dir}"
  COMPOSE_PROJECT_NAME="${ANSIBLE_PROJECT}"
  docker-compose down -v
  rm -rf inventory.tmp \
         conjur.pem
}
function finish {
  rv=$?
  clean || true
  exit $rv
}
trap finish EXIT

while getopts 'e' flag; do
  case "${flag}" in
    e) enterprise="true" ;;
    *) exit 1 ;;
   esac
done

clean

function setup_admin_api_key {
  if [[ "$enterprise" == "true" ]]; then
    docker exec "${cli_cid}" \
      conjur user rotate_api_key
  else
    docker-compose exec -T conjur \
      conjurctl role retrieve-key "${CONJUR_ACCOUNT}:user:admin"
  fi
}

function setup_ansible_api_key {
  docker exec "${cli_cid}" \
    conjur host rotate-api-key -i ansible/ansible-master
}

function hf_token {
  docker exec "${cli_cid}" /bin/sh -c "conjur hostfactory tokens create --duration=24h -i ansible/ansible-factory" | jq -r ".[0].token"
}

function setup_conjur_resources {
  echo "---- setting up conjur ----"
    policy_path="/policy/root.yml"
  docker exec "${cli_cid}" /bin/sh -ec "
    conjur policy load -b root -f ${policy_path}
    conjur variable set -i ansible/target-password -v target_secret_password
  "
}

function run_test_cases {
  for test_case in test_cases/*; do
    # teardown_and_setup
    run_test_case "$(basename -- "$test_case")"
  done
}

function run_test_case {
  echo "---- testing ${test_case} ----"
  local test_case=$1
  if [ -n "$test_case" ]; then
    docker exec "${ansible_cid}" \
      env HFTOKEN="$(hf_token)" \
      env CONJUR_ACCOUNT="${CONJUR_ACCOUNT}" \
      env CONJUR_APPLIANCE_URL="${CONJUR_APPLIANCE_URL}" \
      bash -ec "
        cd tests
        ansible-playbook test_cases/${test_case}/playbook.yml
      "
    if [ -d "${test_dir}/test_cases/${test_case}/tests/" ]; then
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

function teardown_and_setup {
  docker-compose up -d --force-recreate --scale test_app_ubuntu=2 test_app_ubuntu
  docker-compose up -d --force-recreate --scale test_app_centos=2 test_app_centos
}

function wait_for_server {
  # shellcheck disable=SC2016
  docker exec "${cli_cid}" /bin/sh -ec '
    for i in $( seq 20 ); do
      wget --spider -q --tries=1 ${CONJUR_APPLIANCE_URL} && echo "server is up" && break
      echo "."
      sleep 2
    done
  '
}

function fetch_ssl_cert {
  echo "Fetching SSL certs"
  service_id="conjur-proxy-nginx"
  cert_path="cert.crt"
  if [[ "${enterprise}" == "true" ]]; then
    service_id="conjur-master.mycompany.local"
    cert_path="/etc/ssl/certs/ca.pem"
  fi

  (docker-compose exec -T "${service_id}" cat "${cert_path}") > conjur.pem
}

function generate_inventory {
  # Use a different inventory file for docker-compose v1 and v2 or later
  playbook_file="inventory-playbook-v2.yml"
  compose_ver=$(docker-compose version --short)
  if [[ $compose_ver == "1"* ]]; then
    playbook_file="inventory-playbook.yml"
  fi

  # uses .j2 template to generate inventory prepended with COMPOSE_PROJECT_NAME
  docker-compose exec -T ansible bash -ec "
    cd tests
    ansible-playbook $playbook_file
  "

  cat inventory.tmp
}

function setup_conjur_open_source() {

  docker-compose up -d ansible conjur conjur_cli test_app_ubuntu test_app_centos conjur-proxy-nginx

  cli_cid="$(docker-compose ps -q conjur_cli)"

  fetch_ssl_cert
  wait_for_server

  echo "Recreating Conjur CLI with admin credentials"
  CLI_CONJUR_AUTHN_API_KEY=$(setup_admin_api_key)
  docker-compose up --no-deps -d conjur_cli
  cli_cid=$(docker-compose ps -q conjur_cli)

  setup_conjur_resources
}

function setup_conjur_enterprise() {

    echo "Provisioning Enterprise leader and follower"
    docker-compose up -d conjur_appliance
    docker exec conjur_appliance evoke configure master \
    --accept-eula \
    --hostname conjur-server \
    --master-altnames $(hostname -s),$(hostname -f) \
    --admin-password="MySecretP@ss1" \
    demo

    # Run 'sleep infinity' in the CLI container, so the scripts
    # have access to an alive and authenticated CLI until the script terminates
    cli_cid="$(docker-compose run --no-deps -d \
      -w /src/cli \
      --entrypoint sleep client infinity)"

    echo "Authenticate Conjur CLI container"
    docker exec "${cli_cid}" \
      /bin/sh -c "
      echo y | conjur init -u ${CONJUR_APPLIANCE_URL} -a ${CONJUR_ACCOUNT} --force --self-signed
      conjur login -i admin -p MySecretP@ss1
      hostname -i
      "

    CLI_CONJUR_AUTHN_API_KEY=$(setup_admin_api_key)

    docker cp "${cli_cid}":/root/conjur-server.pem .
    mv conjur-server.pem conjur.pem
    # fetch_ssl_cert
    echo "---- before setup_conjur_resources ----"
    setup_conjur_resources

    echo "Relocate credential files"
}

function main() {
  if [[ "${enterprise}" == "true" ]]; then
    echo "Deploying Conjur Enterprise"

    export DOCKER_NETWORK="dap_net"
    export CONJUR_APPLIANCE_URL=https://conjur-server:443
    export CONJUR_ACCOUNT="demo"
    COMPOSE_PROJECT_NAME="${ENTERPRISE_PROJECT}"
    DOCKER_NETWORK="dap_net"

    setup_conjur_enterprise
  else
    echo "Deploying Conjur Open Source"

    export CONJUR_APPLIANCE_URL="https://conjur-proxy-nginx"
    export CONJUR_ACCOUNT="cucumber"
    COMPOSE_PROJECT_NAME="${ANSIBLE_PROJECT}"
    export DOCKER_NETWORK="default"

    setup_conjur_open_source
  fi

  echo "Preparing Ansible for test run"
  COMPOSE_PROJECT_NAME="${ANSIBLE_PROJECT}"
  ANSIBLE_CONJUR_AUTHN_API_KEY=$(setup_ansible_api_key)
  docker-compose up -d ansible
  ansible_cid=$(docker-compose ps -q ansible)
  generate_inventory

  echo "Running tests"
  teardown_and_setup
  run_test_cases

}

main