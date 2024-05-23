#!/bin/bash -eux
set -o pipefail
source "$(git rev-parse --show-toplevel)/dev/util.sh"

function run_test_cases {
  for test_case in test_cases/*; do
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

    # If env vars were provided, load them
    if [ -e 'test_cases/${test_case}/env' ]; then
      . ./test_cases/${test_case}/env
    fi

    # You can add -vvvvv here for debugging
    export SAMPLE_KEY='set_in_env'
    ansible-playbook --extra-vars 'sample_key=set_in_extravars' 'test_cases/${test_case}/playbook.yml'

    py.test --junitxml='./junit/${test_case}' \
      --connection docker \
      -v 'test_cases/${test_case}/tests/test_default.py'
  "
}

run_test_cases
