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
else
  echo "ERROR: Unsupported authn_type '$AUTHN_TYPE'. Supported types are: api_key, iam, azure, gcp." 1>&2
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

  docker exec "$(ansible_cid)" bash -exc "
    cd tests/conjur_variable

    # If env vars were provided for the test case, load them
    if [ -e '$TEST_DIR/${test_case}/env' ]; then
      . ./$TEST_DIR/${test_case}/env
    fi

    # Set environment variables if needed
    export SAMPLE_KEY='set_in_env'

    # Run the Ansible playbook for the test case
    ansible-playbook --extra-vars 'sample_key=set_in_extravars' '$TEST_DIR/${test_case}/playbook.yml'

    # Run the Python tests with JUnit XML output
    py.test --junitxml='./junit/${test_case}' \
      --connection docker \
      -v '$TEST_DIR/${test_case}/tests/test_default.py'
  "
}

run_test_cases
