#!/bin/bash
set -ex

declare -x DOCKER_NETWORK=''

declare -x ENTERPRISE='false'
declare -x CLOUD='false'
declare -x ANSIBLE_API_KEY=''
declare -x ADMIN_API_KEY=''

declare -x ANSIBLE_VERSION='11'
declare -x PYTHON_VERSION='3.13'

source "$(git rev-parse --show-toplevel)/dev/util.sh"

function help {
  cat <<EOF
Conjur Ansible Collection :: Dev Environment

$0 [options]

-e            Deploy Conjur Enterprise. (Default: Conjur Open Source)
-c            Deploy Conjur Cloud. (Developers should not use this option to start a local environment.)
-h, --help    Print usage information.
-p <version>  Run the Ansible service with the desired Python version. (Default: 3.11)
-v <version>  Run the Ansible service with the desired Ansible Community Package
              version. (Default: 8)
EOF
}

while true ; do
  case "$1" in
    -e ) ENTERPRISE="true" ; shift ;;
    -c )  
      if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Cannot setup a local environment using Conjur Cloud"
        exit 1
      fi
      CLOUD="true"
      shift ;;
    -h | --help ) help && exit 0 ;;
    -p ) PYTHON_VERSION="$2" ; shift ; shift ;;
    -v ) ANSIBLE_VERSION="$2" ; shift ; shift ;;
    * )
      if [[ -z "$1" ]]; then
        break
      else
        echo "$1 is not a valid option"
        help
        exit 1
      fi ;;
  esac
done

function clean {
  cd "$(dev_dir)"
  ./stop.sh
}
trap clean ERR

function setup_conjur_resources {
  echo "---- setting up Conjur resources ----"

  policy_path="root.yml"
  if [[ "$ENTERPRISE" == "false" ]]; then
    policy_path="/policy/$policy_path"
  fi

  docker exec "$(cli_cid)" /bin/sh -c "
    conjur policy load -b root -f $policy_path
    conjur variable set -i ansible/target-password -v target_secret_password
    conjur variable set -i ansible/test-secret -v test_secret_password
    conjur variable set -i ansible/test-secret-in-file -v test_secret_in_file_password
    conjur variable set -i 'ansible/var with spaces' -v var_with_spaces_secret_password
  "
}

function deploy_conjur_open_source() {
  echo "---- deploying Conjur Open Source ----"

  # start conjur server
  docker compose up -d --build conjur conjur-proxy-nginx
  set_conjur_cid "$(docker compose ps -q conjur)"
  wait_for_conjur

  # get admin credentials
  fetch_conjur_cert "$(docker compose ps -q conjur-proxy-nginx)" "cert.crt"
  ADMIN_API_KEY="$(user_api_key "$CONJUR_ACCOUNT" admin)"

  # start conjur cli and configure conjur
  docker compose up --no-deps -d conjur_cli
  set_cli_cid "$(docker compose ps -q conjur_cli)"
  setup_conjur_resources
}

function deploy_conjur_enterprise {
  echo "---- deploying Conjur Enterprise ----"

  ensure_submodules

  pushd ./conjur-intro
    # start conjur leader and follower
    ./bin/dap --provision-master
    ./bin/dap --provision-follower
    set_conjur_cid "$(docker compose ps -q conjur-master.mycompany.local)"

    fetch_conjur_cert "$(conjur_cid)" "/etc/ssl/certs/ca.pem"

    # Run 'sleep infinity' in the CLI container so it stays alive
    set_cli_cid "$(docker compose run --no-deps -d -w /src/cli --entrypoint sleep client infinity)"
    # Authenticate the CLI container
    docker exec "$(cli_cid)" /bin/sh -c "
      if [ ! -e /root/conjur-demo.pem ]; then
        echo y | conjur init -u ${CONJUR_APPLIANCE_URL} -a ${CONJUR_ACCOUNT} --force --self-signed
      fi
      conjur login -i admin -p MySecretP@ss1
    "
    # configure conjur
    cp ../policy/root.yml . && setup_conjur_resources
  popd
}

# deploy conjur cloud
function url_encode() {
  printf '%s' "$1" | jq -sRr @uri
}

function set_conjur_cloud_variable() {
  local variable_name="$1"
  local data="$2"
  local encoded_variable_name
  encoded_variable_name=$(url_encode "$variable_name")
  curl -w "%{http_code}" -H "Authorization: Token token=\"$INFRAPOOL_CONJUR_AUTHN_TOKEN\"" \
       -X POST --data-urlencode "${data}" "${CONJUR_APPLIANCE_URL}/secrets/conjur/variable/${encoded_variable_name}"
}

function deploy_conjur_cloud() {
  curl -w "%{http_code}" -H "Authorization: Token token=\"$INFRAPOOL_CONJUR_AUTHN_TOKEN\"" \
       -X POST -d "$(cat ./cloud/root.yml)" "${CONJUR_APPLIANCE_URL}/policies/conjur/policy/data"

  set_conjur_cloud_variable "data/ansible/target-password" "target_secret_password"
  set_conjur_cloud_variable "data/ansible/test-secret" "test_secret_password"
  set_conjur_cloud_variable "data/ansible/test-secret-in-file" "test_secret_in_file_password"
  set_conjur_cloud_variable "data/ansible/var with spaces" "var_with_spaces_secret_password"
}

function deploy_ansible() {
  set_network "$1"
  # get conjur credentials for ansible
  ANSIBLE_API_KEY="$(host_api_key 'ansible/ansible-master')"
  refresh_access_token "host/ansible/ansible-master" "$ANSIBLE_API_KEY"
  docker compose up -d --build ansible
}


function main() {
  # remove previous environment
  clean
  mkdir -p tmp

  # build the ansible-conjur-collection
  repo_dir=$(git rev-parse --show-toplevel)
  $repo_dir/ci/build_release
  archive_name=$(find $repo_dir -name "cyberark-conjur-*tar.gz")
  test -f "$archive_name" && mv "$archive_name" "$(dev_dir)"

  if [[ "$ENTERPRISE" == "true" ]]; then
    export CONJUR_APPLIANCE_URL='https://conjur-master.mycompany.local'
    export CONJUR_ACCOUNT='demo'
    DOCKER_NETWORK='dap_net'
    # start conjur enterprise leader and follower
    deploy_conjur_enterprise
    #start ansible control node
    deploy_ansible "$DOCKER_NETWORK"
  elif [[ "$CLOUD" == "true" ]]; then
    #disable the debugging
    set +x
    export CONJUR_APPLIANCE_URL="$INFRAPOOL_CONJUR_APPLIANCE_URL/api"
    export CONJUR_ACCOUNT=conjur
    export CONJUR_AUTHN_LOGIN=$INFRAPOOL_CONJUR_AUTHN_LOGIN
    echo "$INFRAPOOL_CONJUR_AUTHN_TOKEN" | base64 --decode > "$(dev_dir)/access_token"
    export CONJUR_AUTHN_TOKEN_FILE="$(dev_dir)/access_token"
    set_token "$INFRAPOOL_CONJUR_AUTHN_TOKEN"
    set_appliance_url "$CONJUR_APPLIANCE_URL" 
    test -f "$(dev_dir)/cloud_ca.pem" && cp "$(dev_dir)/cloud_ca.pem" "$(dev_dir)/conjur.pem"
    DOCKER_NETWORK='default'
    #upload the policy into cloud tenant pool
    deploy_conjur_cloud
    #Enable the debugging
    set -x
    set_network "$DOCKER_NETWORK"
    # start ansible control node
    docker compose -f docker-compose.cloud.yml up -d --build ansible
  else
    export CONJUR_APPLIANCE_URL='https://conjur-proxy-nginx'
    export CONJUR_ACCOUNT='cucumber'
    DOCKER_NETWORK='default'
    # start conjur server and proxy
    deploy_conjur_open_source
    #start ansible control node
    deploy_ansible "$DOCKER_NETWORK"
  fi

  set_ansible_cid "$(docker compose ps -q ansible)"

  # scale ansible managed nodes
  generate_inventory
  teardown_and_setup_inventory
  setup_conjur_identities
}

main
