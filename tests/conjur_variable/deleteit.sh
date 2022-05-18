#!/bin/bash -e

# set -o pipefail


# normalises project name by filtering non alphanumeric characters and transforming to lowercase
declare -x COMPOSE_PROJECT_NAME
COMPOSE_PROJECT_NAME=$(echo "${BUILD_TAG:-ansible-plugin-testing}-conjur-variable" | sed -e 's/[^[:alnum:]]//g' | tr '[:upper:]' '[:lower:]')

declare -x ANSIBLE_MASTER_AUTHN_API_KEY=''
declare -x CONJUR_ADMIN_AUTHN_API_KEY=''
declare -x ANSIBLE_CONJUR_CERT_FILE=''

function main() {

  echo " stage 1 "
  pwd
  ls
  cd tests
  cd conjur_variable

  docker-compose up -d --build conjur_https \

  git clone --single-branch --branch main https://github.com/conjurdemos/conjur-intro.git
  # pushd ./conjur-intro
  cd conjur-intro
  echo " Provision Master"
  ./bin/dap --provision-master
  ./bin/dap --wait-for-master
  ./bin/dap --provision-follower
  ./bin/dap --import-custom-certificates

  echo " Setup Policy "
  # cp ../tests/conjur_variable/policy/root.yml .
  echo " stage 2 "
  pwd
  ls
  cp ../policy/root.yml .

    echo " ========load policy====="
    ./bin/cli conjur policy load --replace root root.yml
    echo " ========Set Variable value ansible/test-secret ====="
    ./bin/cli conjur variable values add ansible/test-secret test_secret_password
     echo " =======Set Variable value ansible/test-secret-in-file ====="
    ./bin/cli conjur variable values add ansible/test-secret-in-file test_secret_in_file_password
     echo " =======Set Variable value ansible/var with spaces ====="
    # ./bin/cli conjur variable values add "ansible/var with spaces" var_with_spaces_secret_password
     # echo "Fetching SSL certs"

     echo "Fetching admin API key"
     CONJUR_ADMIN_AUTHN_API_KEY="$(./bin/cli conjur user rotate_api_key|tail -n 1| tr -d '\r')"
    #  CONJUR_ADMIN_AUTHN_API_KEY=$(docker-compose exec -T conjur conjurctl role retrieve-key cucumber:user:admin)
     echo "admin api key: ${CONJUR_ADMIN_AUTHN_API_KEY}"
     api_key=$CONJUR_ADMIN_AUTHN_API_KEY
     echo "${CONJUR_ADMIN_AUTHN_API_KEY}" > api_key
     cp api_key ../

     echo "Recreating conjur CLI with admin credentials"
     # docker-compose up -d conjur_cli
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


      cp conjur-enterprise.pem ../../../tests/conjur_variable

      # echo " stage 3 "
      #       cd ..
      # pwd
      # ls

      # echo " stage 4 "
      # cd ..
      # pwd
      # ls
      # echo " stage 5 "
      # cd ..
      # pwd
      # ls

      # cp conjur-enterprise.pem /tests/conjur_variable

      # # cp conjur-enterprise.pem ../tests/conjur_variable
      # # cp conjur-enterprise.pem ../../../tests/conjur_variable
      echo " stage 6 "
      pwd
      ls
      # echo "Configuring Conjur via CLI"

      # echo "Fetching Ansible master host credentials"
      # ANSIBLE_MASTER_AUTHN_API_KEY=$(docker-compose exec -T conjur_cli conjur host rotate_api_key --host ansible/ansible-master)
      ANSIBLE_CONJUR_CERT_FILE='/cyberark/tests/conjur_variable/conjur-enterprise.pem'

      # echo "Get Access Token"
      #   docker-compose  \
      #   run \
      #   --rm \
      #   -w /src/cli \
      #   --entrypoint /bin/bash \
      #   client \
      #     -c "
      #     export CONJUR_AUTHN_LOGIN=host/ansible/ansible-master
      #     export CONJUR_AUTHN_API_KEY=\"$api_key\"
      #     conjur authn authenticate
      #   " > access_token

      # cp access_token ../../../tests/conjur_variable
      echo " stage 25 "
      pwd
      ls
      cd ..
      echo " stage 46 "
      pwd
      ls
      cd ..
      echo " stage 47 "
      pwd
      ls
      cd ..
      echo " stage 25 "
      pwd
      ls
      cd tests
      echo " stage 25 "
      pwd
      ls
      cd conjur_variable
      echo " stage 25 "
      pwd
      ls
      echo "Preparing Ansible for test run"
      docker-compose up -d --build ansible

      echo "Running tests"
      run_test_cases

}

# function setup_access_token {
#   docker-compose exec -T conjur_cli bash -c "
#     export CONJUR_AUTHN_LOGIN=host/ansible/ansible-master
#     export CONJUR_AUTHN_API_KEY=\"$ANSIBLE_MASTER_AUTHN_API_KEY\"
#     conjur authn authenticate
#   " > access_token
# }

function run_test_cases {

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
