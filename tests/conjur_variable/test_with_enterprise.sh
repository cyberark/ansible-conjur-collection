#!/bin/bash -eu



# normalises project name by filtering non alphanumeric characters and transforming to lowercase
declare -x COMPOSE_PROJECT_NAME
COMPOSE_PROJECT_NAME=$(echo "${BUILD_TAG:-ansible-plugin-testing}-conjur-variable" | sed -e 's/[^[:alnum:]]//g' | tr '[:upper:]' '[:lower:]')
export COMPOSE_PROJECT_NAME

declare -x ANSIBLE_MASTER_AUTHN_API_KEY=''
declare -x CONJUR_ADMIN_AUTHN_API_KEY=''
declare -x ANSIBLE_CONJUR_CERT_FILE=''
declare -x api_key=''

function main() {

git clone --single-branch --branch main https://github.com/conjurdemos/conjur-intro.git
# pushd ./conjur-intro
cd conjur-intro
echo " Provision Master"
  ./bin/dap --provision-master
  ./bin/dap --wait-for-master
  ./bin/dap --provision-follower

  ./bin/dap --import-custom-certificates

  echo " Setup Policy "
  # cp ../policy/root.yml .

  # cd ..
  # cp -r tests/conjur_variable/policy/root.yml conjur-intro/
  # cd conjur-intro

    cp ../tests/conjur_variable/policy/root.yml .

    echo " ========load policy====="
    # ./bin/cli conjur policy load root root.yml
    ./bin/cli conjur policy load --replace root root.yml
    echo " ========Set Variable value ansible/test-secret ====="
    ./bin/cli conjur variable values add ansible/test-secret test_secret_password
     echo " =======Set Variable value ansible/test-secret-in-file ====="
    ./bin/cli conjur variable values add ansible/test-secret-in-file test_secret_in_file_password
     echo " =======Set Variable value ansible/var with spaces ====="
    # ./bin/cli conjur variable values add "ansible/var with spaces" var_with_spaces_secret_password



  echo " Setup CLI "

    docker-compose  \
    run \
    --rm \
    -w /src/cli \
    --entrypoint /bin/bash \
    client \
      -c "cp /root/conjur-demo.pem conjur-enterprise.pem
      conjur host rotate_api_key --host ansible/ansible-master
      "


  ANSIBLE_MASTER_AUTHN_API_KEY=$(docker-compose exec -T client conjur host rotate_api_key --host ansible/ansible-master)
  ANSIBLE_CONJUR_CERT_FILE='/cyberark/tests/conjur-enterprise.pem'

  docker-compose exec -T client bash -c "
    export CONJUR_AUTHN_LOGIN=host/ansible/ansible-master
    export CONJUR_AUTHN_API_KEY=\"$ANSIBLE_MASTER_AUTHN_API_KEY\"
    conjur authn authenticate
  " > access_token

 cp access_token ../tests/conjur_variable


  # cp conjur-enterprise.pem ../

  cp conjur-enterprise.pem ../tests/conjur_variable

  echo " =======55====="
  pwd
  ls

  CONJUR_ADMIN_AUTHN_API_KEY="$(./bin/cli conjur user rotate_api_key|tail -n 1| tr -d '\r')"
  echo "admin api key: ${CONJUR_ADMIN_AUTHN_API_KEY}"
  api_key=$CONJUR_ADMIN_AUTHN_API_KEY
  echo "${CONJUR_ADMIN_AUTHN_API_KEY}" > api_key
  cp api_key ../

  echo " stage 25 "
  pwd
  ls

  cd ..
  echo " stage 25 "
  pwd
  ls
  # popd
  cd tests
  echo " stage 27 "
  pwd
  ls
  cd conjur_variable
  echo " stage 27 "
  pwd
  ls
  echo "Waiting for Conjur server to come up"
  # wait_for_conjur

  echo "Fetching SSL certs"
  fetch_ssl_certs

  echo "Fetching admin API key"
  # CONJUR_ADMIN_AUTHN_API_KEY=$(docker-compose exec -T conjur conjurctl role retrieve-key cucumber:user:admin)

  # echo "Recreating conjur CLI with admin credentials"
  # docker-compose up -d client

  # echo "Configuring Conjur via CLI"
  # # setup_conjur

  # echo "Fetching Ansible master host credentials"
  # ANSIBLE_MASTER_AUTHN_API_KEY=$(docker-compose exec -T conjur_cli conjur host rotate_api_key --host ansible/ansible-master)
  # ANSIBLE_CONJUR_CERT_FILE='/cyberark/tests/conjur.pem'

  ANSIBLE_CONJUR_CERT_FILE='/cyberark/tests/conjur_variable/conjur-enterprise.pem'

  # echo "Get Access Token"
  # setup_access_token

  # echo "Preparing Ansible for test run"
  docker-compose up -d --build ansible

  echo "Running tests"
  run_test_cases
  echo " End of the tests "
}

# function wait_for_conjur {
#  docker-compose exec -T conjur conjurctl wait -r 30 -p 3000
# }

function fetch_ssl_certs {
echo "Running fetch_ssl_certs"
#     docker-compose  \
#     run \
#     --rm \
#     --entrypoint /bin/bash \
#     conjur_https \
#       -c "cat cert.crt > conjur.pem"

docker-compose up -d --build conjur_https
# docker-compose exec -T conjur_https cat cert.crt > conjur.pem
echo "fetch_ssl_certs end "
}

# function setup_conjur {
#   docker-compose exec -T conjur_cli bash -c '
#     conjur policy load root /policy/root.yml
#     conjur variable values add ansible/test-secret test_secret_password
#     conjur variable values add ansible/test-secret-in-file test_secret_in_file_password
#     conjur variable values add "ansible/var with spaces" var_with_spaces_secret_password
#   '
# }

# cat << ENV > .env
# CONJUR_AUTHN_API_KEY=$api_key
# CONJUR_ACCOUNT=demo
# CONJUR_HOST=https://conjur-master.mycompany.local
# ENTERPRISE_TESTS=1
# CERT_DIR=/etc/ssl/certs
# SSL_CERT_FILE=ca.pem
# CONJUR_CERT_FILE=conjur-master.mycompany.local.pem
# CONJUR_KEY_FILE=conjur-master.mycompany.local.key
# ENV

  # -e "CONJUR_APPLIANCE_URL=https://conjur-master.mycompany.local" \
  # -e "CONJUR_ACCOUNT=demo" \
  # -e "CONJUR_AUTHN_LOGIN=admin" \
  # -e "CONJUR_AUTHN_API_KEY=${api_key}" \
  # -e "CONJUR_CERT_FILE=/conjur-enterprise.pem" \
  # -e "CONJUR_AUTHN_TOKEN_FILE=/api_key" \

# function setup_access_token {
# docker-compose exec -T client bash -c "
#  export CONJUR_AUTHN_LOGIN=host/ansible/ansible-master
# export CONJUR_AUTHN_API_KEY=\"$ANSIBLE_MASTER_AUTHN_API_KEY\"
#  conjur authn authenticate
# " > access_token
# }

function run_test_cases {
echo "Running tests cases "
  test_case="retrieve-variable"
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
main
