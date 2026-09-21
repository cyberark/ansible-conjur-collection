#!/bin/bash -eux
set -o pipefail
source "$(git rev-parse --show-toplevel)/dev/util.sh"

AUTHN_TYPE="${1:-api_key}"

if [ "$AUTHN_TYPE" == "api_key" ]; then
  TEST_DIR="test_cases/api_key"
elif [ "$AUTHN_TYPE" == "iam" ]; then
  TEST_DIR="test_cases/iam"
elif [ "$AUTHN_TYPE" == "azure" ]; then
  TEST_DIR="test_cases/azure"
elif [ "$AUTHN_TYPE" == "gcp" ]; then
  TEST_DIR="test_cases/gcp"
elif [ "$AUTHN_TYPE" == "authn-cert" ]; then
  TEST_DIR="test_cases/authn_cert"
elif [ "$AUTHN_TYPE" == "jwt-oidc" ]; then
  TEST_DIR="test_cases/jwt-oidc"
else
  echo "ERROR: Unsupported authn_type '$AUTHN_TYPE'. Supported types are: api_key, iam, azure, gcp, authn-cert, jwt-oidc." 1>&2
  exit 1
fi

function run_test_cases {
  for test_case in "$TEST_DIR"/*; do
    run_test_case "$(basename -- "$test_case")"
  done
}

function run_test_case {
  local test_case="$1"
  echo "---- testing ${test_case} ----"

  if [ -z "$test_case" ]; then
    echo ERROR: run_test_case called with no argument 1>&2
    exit 1
  fi

  # The access token file used by CONJUR_AUTHN_TOKEN_FILE is generated once at
  # deploy time and expires (default Conjur access token TTL is 8 minutes).
  # By the time later test cases run, it may be stale, so refresh it right
  # before any test case that actually relies on it.
  if [ "$AUTHN_TYPE" == "api_key" ] && grep -q "CONJUR_AUTHN_TOKEN_FILE" "$TEST_DIR/${test_case}/env" 2>/dev/null; then
    refresh_ansible_access_token
  fi

  docker exec "$(ansible_cid)" bash -exc "
    cd tests/conjur_variable

    # If env vars were provided for the test case, load them
    if [ -e '$TEST_DIR/${test_case}/env' ]; then
      . ./$TEST_DIR/${test_case}/env
    fi

    # Set environment variables if needed
    export SAMPLE_KEY='set_in_env'

    # Run the Ansible playbook for the test case, capturing its output so
    # test cases can assert on warnings (e.g. insecure file permissions)
    # that Ansible only prints to the console rather than to an artifact file.
    ansible-playbook --extra-vars 'sample_key=set_in_extravars' '$TEST_DIR/${test_case}/playbook.yml' \
      2>&1 | tee '/tmp/ansible-playbook-${test_case}.log'

    # Run the Python tests with JUnit XML output
    py.test --junitxml='./junit/${test_case}' \
      --connection docker \
      -v '$TEST_DIR/${test_case}/tests/test_default.py'
  "
}

run_test_cases
