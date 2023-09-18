#!/bin/bash

function dev_dir {
  repo="$(git rev-parse --show-superproject-working-tree)"
  if [[ "$repo" == "" ]]; then
    repo="$(git rev-parse --show-toplevel)"
  fi

  echo "$repo/dev"
}

function compose_major_version {
  docker-compose version --short | cut -d "." -f 1
}

function set_network {
  echo "$1" > "$(dev_dir)/tmp/docker_network"
}

function network {
  cat "$(dev_dir)/tmp/docker_network"
}

function set_cli_cid {
  echo "$1" > "$(dev_dir)/tmp/cli_cid"
}

function cli_cid {
  cat "$(dev_dir)/tmp/cli_cid"
}

function set_conjur_cid {
  echo "$1" > "$(dev_dir)/tmp/conjur_cid"
}

function conjur_cid {
  cat "$(dev_dir)/tmp/conjur_cid"
}

function set_ansible_cid {
  echo "$1" > "$(dev_dir)/tmp/ansible_cid"
}

function ansible_cid {
  cat "$(dev_dir)/tmp/ansible_cid"
}

function wait_for_conjur {
  docker exec "$(conjur_cid)" conjurctl wait -p 3000
}

function fetch_conjur_cert {
  local cid="$1"
  local cert_path="$2"

  (docker exec "$cid" cat "$cert_path") > "$(dev_dir)/conjur.pem"
}

function user_api_key {
  local account="$1"
  local id="$2"
  docker exec "$(conjur_cid)" conjurctl role retrieve-key "$account:user:$id"
}

function rotate_api_key {
  docker exec "$(cli_cid)" conjur user rotate_api_key
}

function host_api_key {
  local id="$1"
  docker exec "$(cli_cid)" conjur host rotate-api-key -i "$id"
}

function hf_token {
  docker exec "$(cli_cid)" /bin/sh -c "
    conjur hostfactory tokens create --duration=24h -i ansible/ansible-factory
  " | jq -r ".[0].token"
}

function refresh_access_token {
  local id="$1"
  local api_key="$2"
  docker exec "$(cli_cid)" /bin/sh -c "
    export CONJUR_AUTHN_LOGIN=$id
    export CONJUR_AUTHN_API_KEY=$api_key
    conjur authenticate
  " > "$(dev_dir)/access_token"
}

function teardown_and_setup_inventory {
  pushd "$(dev_dir)"
    # shellcheck disable=SC2155
    export DOCKER_NETWORK="$(network)"
    docker-compose up -d --force-recreate --scale test_app_ubuntu=2 test_app_ubuntu
    docker-compose up -d --force-recreate --scale test_app_centos=2 test_app_centos
  popd
}

function setup_conjur_identities {
  docker exec \
    -e HFTOKEN="$(hf_token)" \
    "$(ansible_cid)" bash -ec "
      cd dev
      ansible-playbook playbooks/conjur-identity-setup/conjur_role_playbook.yml
    "
}

function generate_inventory {
  docker exec "$(ansible_cid)" bash -ec "
    cd dev
    ansible-playbook playbooks/inventory-setup/inventory-playbook.yml \
      -e \"compose_version=$(compose_major_version)\"
  "
}

function ensure_submodules {
  if [ ! -d "$(dev_dir)/conjur-intro" ]; then
    git submodule init -- "$(dev_dir)/conjur-intro"
    git submodule update --remote -- "$(dev_dir)/conjur-intro"
  fi
}

function clean_submodules {
  if [ -d "$(dev_dir)/conjur-intro" ]; then
    pushd "$(dev_dir)/conjur-intro"
      git clean -df
    popd
  fi
}
