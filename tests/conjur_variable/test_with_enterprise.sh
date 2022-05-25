#!/bin/bash -eu


# normalises project name by filtering non alphanumeric characters and transforming to lowercase
declare -x COMPOSE_PROJECT_NAME
COMPOSE_PROJECT_NAME=$(echo "${BUILD_TAG:-ansible-plugin-testing}-conjur-variable" | sed -e 's/[^[:alnum:]]//g' | tr '[:upper:]' '[:lower:]')
export COMPOSE_PROJECT_NAME

declare -x ANSIBLE_MASTER_AUTHN_API_KEY=''
declare -x CONJUR_ADMIN_AUTHN_API_KEY=''
declare -x ANSIBLE_CONJUR_CERT_FILE=''

function main() {

    git clone --single-branch --branch main https://github.com/conjurdemos/conjur-intro.git
  pushd ./conjur-intro

      echo " Provision Master"
      ./bin/dap --provision-master
      ./bin/dap --provision-follower

      echo " Setup Policy "
      echo " ========load policy====="
      cp ../tests/conjur_variable/policy/root.yml .
      ./bin/cli conjur policy load root root.yml
            # cp ../tests/conjur_variable/conjur.yml .
            # ./bin/cli conjur policy load --replace root conjur.yml
            # ./bin/cli conjur policy load root conjur.yml
      echo " ========Set Variable value ansible/test-secret ====="
      ./bin/cli conjur variable values add ansible/test-secret test_secret_password
      echo " =======Set Variable value ansible/test-secret-in-file ====="
      ./bin/cli conjur variable values add ansible/test-secret-in-file test_secret_in_file_password
      echo " =======Set Variable value ansible/var with spaces ====="
      # ./bin/cli conjur variable values add "ansible/var with spaces" var_with_spaces_secret_password

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
        # docker-compose  \
        # run \
        # --rm \
        # -w /src/cli \
        # --entrypoint /bin/bash \
        # client \
        #   -ec 'cp /root/conjur-demo.pem conjur-enterprise.pem
        #   conjur variable values add "ansible/var with spaces" var_with_spaces_secret_password
        #   '

        docker-compose  \
        run \
        --rm \
        -w /src/cli \
        --entrypoint /bin/bash \
        client \
          -c "
              cp /root/conjur-demo.pem conjur-enterprise.pem
              conjur variable values add "ansible/var with spaces" var_with_spaces_secret_password
              export CONJUR_AUTHN_LOGIN=host/ansible/ansible-master
              export CONJUR_AUTHN_API_KEY=\"$ANSIBLE_MASTER_AUTHN_API_KEY\"
              conjur authn authenticate
            " > access_token

        cp access_token ../tests/conjur_variable
        cp conjur-enterprise.pem ../tests/conjur_variable

      conjur_enterprise=$(cat conjur-enterprise.pem)
      echo "conjur-enterprise.pem: ${conjur_enterprise}"

      access_token=$(cat access_token)
      echo "access_token: ${access_token}"

      echo " Get CONJUR_ADMIN_AUTHN_API_KEY value "
      CONJUR_ADMIN_AUTHN_API_KEY="$(./bin/cli conjur user rotate_api_key|tail -n 1| tr -d '\r')"
      echo "CONJUR_ADMIN_AUTHN_API_KEY: ${CONJUR_ADMIN_AUTHN_API_KEY}"
  popd

  pushd ./tests/conjur_variable

      docker build -t conjur_ansible:v1 .

      echo " Run Ansible "
       docker run \
       -d -t \
       --name ansible_container \
       --volume "$(git rev-parse --show-toplevel):/cyberark" \
       --volume "$(git rev-parse --show-toplevel)/plugins":/root/.ansible/plugins \
       --network dap_net \
       -e "CONJUR_APPLIANCE_URL=https://conjur-master.mycompany.local" \
       -e "CONJUR_ACCOUNT=demo" \
       -e "CONJUR_AUTHN_LOGIN=admin" \
       -e "ANSIBLE_MASTER_AUTHN_API_KEY=${ANSIBLE_MASTER_AUTHN_API_KEY}" \
       -e "CONJUR_ADMIN_AUTHN_API_KEY=${CONJUR_ADMIN_AUTHN_API_KEY}" \
       -e "ANSIBLE_CONJUR_CERT_FILE=/cyberark/tests/conjur-enterprise.pem" \
       -e "CONJUR_AUTHN_API_KEY=${CONJUR_ADMIN_AUTHN_API_KEY}" \
       --workdir "/cyberark" \
       conjur_ansible:v1 \

      echo " Ansible logs "
      docker logs ansible_container
      echo " Ansible inspect "
      docker inspect ansible_container

      echo "Running tests"
      run_test_cases
      echo " End of the tests "
  popd
}

function run_test_cases {

  # retrieve-variable-disable-verify-certs
  # retrieve-variable-no-cert-provided

  local test_case="retrieve-variable-with-spaces-secret"
  echo "---- Run test cases ----"
  docker exec -t ansible_container bash -exc "
   pwd
   ls
   cd tests/conjur_variable

        if [ -e 'test_cases/${test_case}/env' ]; then
        . ./test_cases/${test_case}/env
        fi

       ansible-playbook 'test_cases/${test_case}/playbook.yml'

        # py.test --junitxml='./junit/${test_case}' \
        #   --connection docker \
        #   -v 'test_cases/${test_case}/tests/test_default.py'
  "
}

main
