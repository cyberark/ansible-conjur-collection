#!/bin/bash -eu

declare -x ANSIBLE_CONJUR_CERT_FILE=''

git clone --single-branch --branch main https://github.com/conjurdemos/conjur-intro.git
cd conjur-intro
echo " Provision Master"
  ./bin/dap --provision-master
  ./bin/dap --provision-follower

echo " Setup Policy "
  # cp ../policy/root.yml .
  cd ..
  cp -r tests/conjur_variable/policy/root.yml conjur-intro
  cd conjur-intro

    ./bin/cli conjur policy load root root.yml
    ./bin/cli conjur variable values add ansible/test-secret test_secret_password
    ./bin/cli conjur variable values add ansible/test-secret-in-file test_secret_in_file_password
    echo "  facing issues "
    # ./bin/cli conjur variable values add "ansible/var with spaces" var_with_spaces_secret_password
    # ./bin/cli conjur variable values add ansible/target-password target_secret_password

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
  cp conjur-enterprise.pem ../

  CONJUR_ADMIN_AUTHN_API_KEY="$(./bin/cli conjur user rotate_api_key|tail -n 1| tr -d '\r')"
  echo "admin api key: ${CONJUR_ADMIN_AUTHN_API_KEY}"
  echo "${CONJUR_ADMIN_AUTHN_API_KEY}" > ANSIBLE_MASTER_AUTHN_API_KEY
  cp ANSIBLE_MASTER_AUTHN_API_KEY ../

  cd ..

  echo "Waiting for Conjur server to come up"
  # wait_for_conjur

  cd tests/conjur_variable

function main() {

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
  ANSIBLE_MASTER_AUTHN_API_KEY="$(./bin/cli conjur user rotate_api_key|tail -n 1| tr -d '\r')"
  ANSIBLE_CONJUR_CERT_FILE='/cyberark/tests/conjur.pem'

  # echo "Get Access Token"
  # setup_access_token

  # echo "Preparing Ansible for test run"
  docker-compose up -d --build ansible

  echo "Running tests"
  run_test_cases
  echo " End of the tests "
}

function wait_for_conjur {
  docker-compose exec -T conjur conjurctl wait -r 30 -p 3000
}

function fetch_ssl_certs {
 echo "Running fetch_ssl_certs"
 docker-compose up -d --build conjur_https
 docker-compose exec -T conjur_https cat cert.crt > conjur.pem
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

# function setup_access_token {
#   docker-compose exec -T client bash -c "
#     export CONJUR_AUTHN_LOGIN=host/ansible/ansible-master
#     export CONJUR_AUTHN_API_KEY=\"$ANSIBLE_MASTER_AUTHN_API_KEY\"
#     conjur authn authenticate
#   " > access_token
# }

function run_test_cases {

  test_case="retrieve-variable-disable-verify-certs"
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
