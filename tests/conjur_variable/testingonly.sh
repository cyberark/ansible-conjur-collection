#!/bin/bash
set -x
set -e

# Script to run SpringBootExample against Conjur Enterprise (appliance)

# Ensure conjur-intro submodule is checked out
git submodule update --init --recursive

pushd ./conjur-intro
  pwd

  # Provision master and follower
  ./bin/dap --provision-master
  ./bin/dap --provision-follower

  # Load policy required by SpringBootExample
  # conjur.yml must be in the conjur-intro folder for access
  # via docker-compose exec
  cp ../conjur.yml .
  ./bin/cli conjur policy load --replace root conjur.yml

  # # # Set variable values
  ./bin/cli conjur variable values add db/password secret
  ./bin/cli conjur variable values add db/dbuserName 123456
  ./bin/cli conjur variable values add db/dbpassWord 7890123
  ./bin/cli conjur variable values add db/key 456789

  # Retrieve pem
  docker-compose  \
    run \
    --rm \
    -w /src/cli \
    --entrypoint /bin/bash \
    client \
      -c "cp /root/conjur-demo.pem conjur-enterprise.pem"
  cp conjur-enterprise.pem ../

  # docker-compose run --rm -w /src/cli --entrypoint /bin/bash

  # Retrieve Admin API Key
  admin_api_key="$(./bin/cli conjur user rotate_api_key|tail -n 1| tr -d '\r')"
  echo "admin api key: ${admin_api_key}"
  echo "${admin_api_key}" > api_key
  cp api_key ../

popd
pwd

docker run \
  --volume "$(git rev-parse --show-toplevel):/repo" \
  --volume "${PWD}/maven_cache":/root/.m2 \
  --volume "${PWD}/api_key:/api_key" \
  --volume "${PWD}/conjur-enterprise.pem:/conjur-enterprise.pem" \
  --network dap_net \
  -e "CONJUR_APPLIANCE_URL=https://conjur-master.mycompany.local" \
  -e "CONJUR_ACCOUNT=demo" \
  -e "CONJUR_AUTHN_LOGIN=admin" \
  -e "CONJUR_AUTHN_API_KEY=${admin_api_key}" \
  -e "CONJUR_CERT_FILE=/conjur-enterprise.pem" \
  -e "CONJUR_AUTHN_TOKEN_FILE=/api_key" \
  --workdir "/repo" \
  --rm \
  --entrypoint /bin/bash \
  sampleapp \
    -ec 'mvn --batch-mode -f pom.xml jacoco:prepare-agent test jacoco:report'
