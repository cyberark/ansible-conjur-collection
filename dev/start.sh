#!/bin/bash
set -ex

declare -x DOCKER_NETWORK=''

declare -x FLAVOUR='oss'
declare -x AUTHN_TYPE='api_key'

declare -x ANSIBLE_API_KEY=''
declare -x ADMIN_API_KEY=''

declare -x ANSIBLE_VERSION='11'
declare -x PYTHON_VERSION='3.13'

source "$(git rev-parse --show-toplevel)/dev/util.sh"

function help {
  cat <<EOF
Conjur Ansible Collection :: Dev Environment

$0 [options]

-f <flavour>   Specify flavour: oss, enterprise, cloud, edge (Default: oss)
-a <type>    Specify authentication type: iam, azure, gcp, api_key (Default: api_key)
-h, --help             Print usage information.
-p <version>           Run the Ansible service with the desired Python version (Default: 3.11).
-v <version>           Run the Ansible service with the desired Ansible Community Package version.
EOF
}

while true ; do
  case "$1" in
    -f | --flavour ) FLAVOUR="$2" ; shift ; shift ;;
    -a | --authn-type ) AUTHN_TYPE="$2" ; shift ; shift ;;
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

case "$AUTHN_TYPE" in
  "iam" | "azure" | "gcp" | "api_key")
    ;;
  *)
    echo "Invalid authentication type: $AUTHN_TYPE. Valid options are: iam, azure, gcp, api_key."
    exit 1
    ;;
esac

function set_authentication_variables {
  case "$AUTHN_TYPE" in
    "api_key")
      export CONJUR_AUTHN_LOGIN='host/ansible/ansible-master'
      ;;
    "iam")
      export CONJUR_AUTHN_TYPE='aws'
      export CONJUR_AUTHN_SERVICE_ID='prod'
      export CONJUR_AUTHN_LOGIN='host/ansible/601277729239/InstanceReadJenkinsExecutorHostFactoryToken'
      ;;
    "azure")
      export CONJUR_AUTHN_TYPE="azure"
      export CONJUR_AUTHN_LOGIN="host/azure-apps/azureVM"
      export CONJUR_AUTHN_SERVICE_ID="AzureAnsible"
      export AZURE_CLIENT_ID="$USER_ASSIGNED_IDENTITY_CLIENT_ID"
      ;;
    "gcp")
      export CONJUR_AUTHN_TYPE="gcp"
      export CONJUR_AUTHN_LOGIN="host/gcp-apps/test-app"
      GCP_TOKEN_FILE="$(dev_dir)/gcp/token"
      if [ ! -f "$GCP_TOKEN_FILE" ] || [ ! -s "$GCP_TOKEN_FILE" ]; then
        echo "No GCP token found"
        exit 1
      fi
      GCP_TOKEN=$(<"$GCP_TOKEN_FILE")
      AUTHN_URL="https://localhost:443/authn-gcp/${CONJUR_ACCOUNT}/authenticate"
      curl -k -d "jwt=${GCP_TOKEN}" "$AUTHN_URL" > "$(dev_dir)/access_token"
      export CONJUR_AUTHN_TOKEN_FILE="/cyberark/dev/access_token"
      ;;
    *)
      echo "Unknown authentication type: $AUTHN_TYPE"
      exit 1
      ;;
  esac
}

function set_cloud_authentication_variables {
  case "$AUTHN_TYPE" in
    "api_key")
      export CONJUR_AUTHN_LOGIN="host/data/ansible/ansible-master"
      echo "$INFRAPOOL_CONJUR_AUTHN_TOKEN" | base64 --decode > "$(dev_dir)/access_token"
      export CONJUR_AUTHN_TOKEN_FILE="/cyberark/dev/access_token"
      cp -f "$(dev_dir)/docker-compose.cloud.template.yml" "$(dev_dir)/docker-compose.cloud.yml"
      ;;
    "iam")
      export CONJUR_AUTHN_TYPE='aws'
      export CONJUR_AUTHN_SERVICE_ID='prod'
      export CONJUR_AUTHN_LOGIN='host/data/ansible/601277729239/InstanceReadJenkinsExecutorHostFactoryToken'
      sed '/CONJUR_AUTHN_TOKEN_FILE:/d' "$(dev_dir)/docker-compose.cloud.template.yml" > "$(dev_dir)/docker-compose.cloud.yml"
      ;;
    "azure")
      export CONJUR_AUTHN_TYPE="azure"
      export CONJUR_AUTHN_LOGIN="host/data/azure-apps/azureVM"
      export CONJUR_AUTHN_SERVICE_ID="AzureAnsible"
      export AZURE_CLIENT_ID="$USER_ASSIGNED_IDENTITY_CLIENT_ID"
      sed '/CONJUR_AUTHN_TOKEN_FILE:/d' "$(dev_dir)/docker-compose.cloud.template.yml" > "$(dev_dir)/docker-compose.cloud.yml"
      ;;
    "gcp")
      export CONJUR_AUTHN_TYPE="gcp"
      export CONJUR_AUTHN_LOGIN="host/data/gcp-apps/test-app"
      GCP_TOKEN_FILE="$(dev_dir)/gcp/token"
      if [ ! -f "$GCP_TOKEN_FILE" ] || [ ! -s "$GCP_TOKEN_FILE" ]; then
        echo "No GCP token found"
        exit 1
      fi
      GCP_TOKEN=$(<"$GCP_TOKEN_FILE")
      [[ "$FLAVOUR" == "edge" ]] && AUTHN_URL="https://localhost:443/api/authn-gcp/${CONJUR_ACCOUNT}/authenticate" || AUTHN_URL="$CONJUR_APPLIANCE_URL/authn-gcp/${CONJUR_ACCOUNT}/authenticate"
      curl -k -d "jwt=${GCP_TOKEN}" "$AUTHN_URL" > "$(dev_dir)/access_token"
      export CONJUR_AUTHN_TOKEN_FILE="/cyberark/dev/access_token"
      cp -f "$(dev_dir)/docker-compose.cloud.template.yml" "$(dev_dir)/docker-compose.cloud.yml"
      ;;
    *)
      echo "Unknown authentication type: $AUTHN_TYPE"
      exit 1
      ;;
  esac
}

function replaceTemplates() {
  case "$AUTHN_TYPE" in
    "azure")
      if [[ -z "$AZURE_SUBSCRIPTION_ID" || -z "$AZURE_RESOURCE_GROUP" || -z "$USER_ASSIGNED_IDENTITY" ]]; then
        echo "Error: Missing Azure environment variables."
        exit 1
      fi
      for template in "oss_ent/azure/authn-azure-hosts.template.yml" "cloud/azure/authn-azure-hosts.template.yml"; do
        ESCAPED_AZURE_SUBSCRIPTION_ID=$(printf '%s\n' "$AZURE_SUBSCRIPTION_ID" | sed 's/[&/\]/\\&/g')
        ESCAPED_AZURE_RESOURCE_GROUP=$(printf '%s\n' "$AZURE_RESOURCE_GROUP" | sed 's/[&/\]/\\&/g')
        ESCAPED_USER_ASSIGNED_IDENTITY=$(printf '%s\n' "$USER_ASSIGNED_IDENTITY" | sed 's/[&/\]/\\&/g')
        
        sed -e "s#{{ AZURE_SUBSCRIPTION_ID }}#$ESCAPED_AZURE_SUBSCRIPTION_ID#g" \
            -e "s#{{ AZURE_RESOURCE_GROUP }}#$ESCAPED_AZURE_RESOURCE_GROUP#g" \
            -e "s#{{ USER_ASSIGNED_IDENTITY }}#$ESCAPED_USER_ASSIGNED_IDENTITY#g" \
            "policy/$template" > "policy/${template/.template/}"
      done
      ;;
    "gcp")
      GCP_PROJECT=$(cat $(dev_dir)/gcp/project-id)
      ESCAPED_GCP_PROJECT=$(printf '%s\n' "$GCP_PROJECT" | sed 's/[&/\]/\\&/g')
      for template in "oss_ent/gcp/authn-gcp-hosts.template.yml" "cloud/gcp/authn-gcp-hosts.template.yml"; do
        sed -e "s#{{ PROJECT_ID }}#$ESCAPED_GCP_PROJECT#g" \
            "policy/$template" > "policy/${template/.template/}"
      done
      ;;
  esac
}



function clean {
  cd "$(dev_dir)"
  ./stop.sh
}
trap clean ERR

function setup_conjur_resources {
  echo "---- setting up Conjur resources ----"

  policy_path="policy"
  if [[ "$FLAVOUR" == "oss" ]]; then
    policy_path="/policy"
  fi

  case "$AUTHN_TYPE" in
    "api_key")
      docker exec "$(cli_cid)" /bin/sh -c "
        conjur policy load -b root -f $policy_path/oss_ent/api_key/root.yml
        conjur variable set -i ansible/target-password -v target_secret_password
        conjur variable set -i ansible/test-secret -v test_secret_password
        conjur variable set -i ansible/test-secret-in-file -v test_secret_in_file_password
        conjur variable set -i 'ansible/var with spaces' -v var_with_spaces_secret_password
        conjur list
      "
      ;;
    "iam")
      docker exec "$(cli_cid)" /bin/sh -c "
        conjur policy load -b root -f $policy_path/oss_ent/iam/authn-iam.yml
        conjur policy load -b root -f $policy_path/oss_ent/iam/authn-iam-host.yml
        conjur variable set -i ansible/target-password -v target_secret_password
        conjur variable set -i ansible/test-secret -v test_secret_password
        conjur variable set -i ansible/test-secret-in-file -v test_secret_in_file_password
        conjur variable set -i 'ansible/var with spaces' -v var_with_spaces_secret_password
        conjur list
      "
      ;;
    "azure")
      docker exec "$(cli_cid)" /bin/sh -c "
        conjur policy load -b root -f $policy_path/oss_ent/azure/authn-azure-AzureWS.yml
        conjur policy load -b root -f $policy_path/oss_ent/azure/authn-azure-hosts.yml
        conjur policy load -b root -f $policy_path/oss_ent/azure/authn-azure-secrets.yml
        conjur variable set -i conjur/authn-azure/AzureAnsible/provider-uri -v https://sts.windows.net/df242c82-fe4a-47e0-b0f4-e3cb7f8104f1/
        conjur variable set -i ansible/target-password -v target_secret_password
        conjur variable set -i ansible/test-secret -v test_secret_password
        conjur variable set -i ansible/test-secret-in-file -v test_secret_in_file_password
        conjur variable set -i 'ansible/var with spaces' -v var_with_spaces_secret_password
        conjur list
      "
      ;;
    "gcp")
      docker exec "$(cli_cid)" /bin/sh -c "
        conjur policy load -b root -f $policy_path/oss_ent/gcp/authn-gcp.yml
        conjur policy load -b root -f $policy_path/oss_ent/gcp/authn-gcp-hosts.yml
        conjur policy load -b root -f $policy_path/oss_ent/gcp/authn-gcp-secrets.yml
        conjur variable set -i ansible/target-password -v target_secret_password
        conjur variable set -i ansible/test-secret -v test_secret_password
        conjur variable set -i ansible/test-secret-in-file -v test_secret_in_file_password
        conjur variable set -i 'ansible/var with spaces' -v var_with_spaces_secret_password
        conjur list
      "
      ;;
    *)
      echo "Unknown authentication type: $AUTHN_TYPE"
      exit 1
      ;;
  esac
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

  clean_submodules
  ensure_submodules

  pushd ./conjur-intro
    export CONJUR_AUTHENTICATORS="authn,authn-iam/prod,authn-azure/AzureAnsible,authn-gcp"
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
    cp -r ../policy . && setup_conjur_resources
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

  case "$AUTHN_TYPE" in
    "api_key")
      curl -w "%{http_code}" -H "Authorization: Token token=\"$INFRAPOOL_CONJUR_AUTHN_TOKEN\"" \
        -X POST -d "$(cat policy/cloud/api_key/root.yml)" "${CONJUR_APPLIANCE_URL}/policies/conjur/policy/data"
      ;;
    "iam")
      curl -w "%{http_code}" -H "Authorization: Token token=\"$INFRAPOOL_CONJUR_AUTHN_TOKEN\"" \
        -X POST -d "$(cat policy/cloud/iam/authn-iam.yml)" "${CONJUR_APPLIANCE_URL}/policies/conjur/policy/conjur/authn-iam"
      curl -w "%{http_code}" -H "Authorization: Token token=\"$INFRAPOOL_CONJUR_AUTHN_TOKEN\"" \
        -X POST -d "$(cat policy/cloud/iam/authn-iam-host.yml)" "${CONJUR_APPLIANCE_URL}/policies/conjur/policy/data"
      curl -w "%{http_code}" -H "Authorization: Token token=\"$INFRAPOOL_CONJUR_AUTHN_TOKEN\"" \
        -X POST -d "$(cat policy/cloud/iam/authn-permission.yml)" "${CONJUR_APPLIANCE_URL}/policies/conjur/policy/conjur/authn-iam/prod"
      curl -w "%{http_code}" -H "Authorization: Token token=\"$INFRAPOOL_CONJUR_AUTHN_TOKEN\"" \
        -X PATCH  -H 'Content-Type: text/plain' --data-raw 'enabled=true' "${CONJUR_APPLIANCE_URL}/authn-iam/prod/conjur"
      ;;
    "azure")
      curl -w "%{http_code}" -H "Authorization: Token token=\"$INFRAPOOL_CONJUR_AUTHN_TOKEN\"" \
        -X POST -d "$(cat policy/cloud/azure/authn-azure-AzureAnsible.yml)" "${CONJUR_APPLIANCE_URL}/policies/conjur/policy/conjur/authn-azure"
      curl -w "%{http_code}" -H "Authorization: Token token=\"$INFRAPOOL_CONJUR_AUTHN_TOKEN\"" \
        -X POST -d "$(cat policy/cloud/azure/authn-azure-hosts.yml)" "${CONJUR_APPLIANCE_URL}/policies/conjur/policy/data"
      curl -w "%{http_code}" -H "Authorization: Token token=\"$INFRAPOOL_CONJUR_AUTHN_TOKEN\"" \
        -X POST -d "$(cat policy/cloud/azure/authn-azure-secrets.yml)" "${CONJUR_APPLIANCE_URL}/policies/conjur/policy/data"
      curl -w "%{http_code}" -H "Authorization: Token token=\"$INFRAPOOL_CONJUR_AUTHN_TOKEN\"" \
        -X POST -d "$(cat policy/cloud/azure/authn-azure-permission.yml)" "${CONJUR_APPLIANCE_URL}/policies/conjur/policy/conjur/authn-azure/AzureAnsible"
      curl -w "%{http_code}" -H "Authorization: Token token=\"$INFRAPOOL_CONJUR_AUTHN_TOKEN\"" \
        -X PATCH  -H 'Content-Type: text/plain' --data-raw 'enabled=true' "${CONJUR_APPLIANCE_URL}/authn-azure/AzureAnsible/conjur"

      encoded_variable_name=$(url_encode "conjur/authn-azure/AzureAnsible/provider-uri")
      data="https://sts.windows.net/df242c82-fe4a-47e0-b0f4-e3cb7f8104f1/"
      curl -w "%{http_code}" -H "Authorization: Token token=\"$INFRAPOOL_CONJUR_AUTHN_TOKEN\"" \
       -X POST -d "${data}" "${CONJUR_APPLIANCE_URL}/secrets/conjur/variable/${encoded_variable_name}"
      ;;
    "gcp")
      curl -w "%{http_code}" -H "Authorization: Token token=\"$INFRAPOOL_CONJUR_AUTHN_TOKEN\"" \
        -X POST -d "$(cat policy/cloud/gcp/authn-gcp.yml)" "${CONJUR_APPLIANCE_URL}/policies/conjur/policy/conjur/authn-gcp"
      curl -w "%{http_code}" -H "Authorization: Token token=\"$INFRAPOOL_CONJUR_AUTHN_TOKEN\"" \
        -X POST -d "$(cat policy/cloud/gcp/authn-gcp-hosts.yml)" "${CONJUR_APPLIANCE_URL}/policies/conjur/policy/data"
      curl -w "%{http_code}" -H "Authorization: Token token=\"$INFRAPOOL_CONJUR_AUTHN_TOKEN\"" \
        -X POST -d "$(cat policy/cloud/gcp/authn-gcp-secrets.yml)" "${CONJUR_APPLIANCE_URL}/policies/conjur/policy/data"
      curl -w "%{http_code}" -H "Authorization: Token token=\"$INFRAPOOL_CONJUR_AUTHN_TOKEN\"" \
        -X POST -d "$(cat policy/cloud/gcp/authn-gcp-permission.yml)" "${CONJUR_APPLIANCE_URL}/policies/conjur/policy/conjur/authn-gcp"
      curl -w "%{http_code}" -H "Authorization: Token token=\"$INFRAPOOL_CONJUR_AUTHN_TOKEN\"" \
        -X PATCH  -H 'Content-Type: text/plain' --data-raw 'enabled=true' "${CONJUR_APPLIANCE_URL}/authn-gcp/conjur"
      ;;
    *)
      echo "Unknown authentication type: $AUTHN_TYPE"
      exit 1
      ;;
  esac

  set_conjur_cloud_variable "data/ansible/target-password" "target_secret_password"
  set_conjur_cloud_variable "data/ansible/test-secret" "test_secret_password"
  set_conjur_cloud_variable "data/ansible/test-secret-in-file" "test_secret_in_file_password"
  set_conjur_cloud_variable "data/ansible/var with spaces" "var_with_spaces_secret_password"
}

function deploy_ansible() {
  set_network "$1"
  if [[ "$AUTHN_TYPE" == "api_key" ]]; then
    # get conjur credentials for ansible
    ANSIBLE_API_KEY="$(host_api_key 'ansible/ansible-master')"
    refresh_access_token "host/ansible/ansible-master" "$ANSIBLE_API_KEY"
  fi
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
  
  replaceTemplates

  case "$FLAVOUR" in
    "enterprise")
      export CONJUR_APPLIANCE_URL='https://conjur-master.mycompany.local'
      export CONJUR_ACCOUNT='demo'
      DOCKER_NETWORK='dap_net'
      deploy_conjur_enterprise
      set_authentication_variables
      deploy_ansible "$DOCKER_NETWORK"
      set_ansible_cid "$(docker compose ps -q ansible)"
      ;;
    "cloud")
      set +x
      export CONJUR_APPLIANCE_URL="$INFRAPOOL_CONJUR_APPLIANCE_URL/api"
      export CONJUR_ACCOUNT=conjur
      set_token "$INFRAPOOL_CONJUR_AUTHN_TOKEN"
      set_appliance_url "$CONJUR_APPLIANCE_URL"
      test -f "$(dev_dir)/cloud_ca.pem" && cp "$(dev_dir)/cloud_ca.pem" "$(dev_dir)/conjur.pem"
      DOCKER_NETWORK='default'
      deploy_conjur_cloud
      set_network "$DOCKER_NETWORK"
      set_cloud_authentication_variables
      set -x
      docker compose -f docker-compose.cloud.yml up -d --build ansible
      ;;
    "oss")
      export CONJUR_APPLIANCE_URL='https://conjur-proxy-nginx'
      export CONJUR_ACCOUNT='cucumber'
      DOCKER_NETWORK='default'
      deploy_conjur_open_source
      set_authentication_variables
      deploy_ansible "$DOCKER_NETWORK"
      set_ansible_cid "$(docker compose ps -q ansible)"
      ;;
    "edge")
      set +x
      export CONJUR_APPLIANCE_URL="https://edge-test:8443/api"
      export CONJUR_ACCOUNT=conjur
      set_token "$INFRAPOOL_CONJUR_AUTHN_TOKEN"
      set_appliance_url "$CONJUR_APPLIANCE_URL"
      DOCKER_NETWORK='default'
      set_network "$DOCKER_NETWORK"
      set_cloud_authentication_variables
      set -x
      docker compose -f docker-compose.cloud.yml up -d --build ansible
      openssl s_client -connect localhost:443 -showcerts </dev/null 2>/dev/null | openssl x509 -outform PEM > "$(dev_dir)/conjur.pem"
      # Adding edge to the docker network
      docker network inspect dev_default --format '{{json .Containers}}' | grep -q 'edge-test' || docker network connect dev_default edge-test
      ;;
    *)
      echo "Invalid Conjur Flavour: $FLAVOUR. Please choose one of: oss, enterprise, cloud, edge."
      exit 1
      ;;
  esac
  set_ansible_cid "$(docker compose ps -q ansible)"
  generate_inventory
  teardown_and_setup_inventory
  [[ "$FLAVOUR" != "edge" ]] && setup_conjur_identities || exit 0
}

main
