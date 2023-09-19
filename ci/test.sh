#!/bin/bash -ex
source "$(git rev-parse --show-toplevel)/dev/util.sh"

# Test runner for Ansible Conjur Collection

# Test subdirectors containing a `test.sh` file
test_directories=("conjur_variable")

# Roles containing a test subdirectory
role_directories=("conjur_host_identity")

# Target directory that can be manually set by passing a value to the `-d` flag
target=""

# Flags to be applied to testing scripts
flags=""

# Indicate whether to start a new test env or use an existing one
start_dev_env="true"

function help {
  cat <<EOF
Conjur Ansible Collection :: Test runner

$0 [options]

-a            Run all test files in default test directories.
-d            Run tests against the existing development environment. This option
              overrides -e, -p and -v in favor of existing services.
-e            Deploy Conjur Enterprise. (Default: Conjur Open Source)
-h            Print usage information.
-p <version>  Run the Ansible service with the desired Python version. (Default: 3.11)
-t            Run test files in a given directory. Valid options are:
                ${test_directories[*]} ${role_directories[*]} all
-v <version>  Run the Ansible service with the desired Ansible Community Package
              version. (Default: 8)
EOF
}

# Run a `test.sh` file in a given subdirectory of the top-level `tests` directory
# Expected directory structure is "tests/<plugin>/test.sh"
function run_test {
  pushd "${PWD}/tests/${1}"
    echo "Running ${1} tests..."
    ./test.sh
  popd
}

# Run a `test.sh` file for a given role
# Expected directory structure is "roles/<role>/tests/test.sh"
function run_role_test {
  pushd "${PWD}/roles/${1}/tests"
    echo "Running ${1} tests..."
    ./test.sh
  popd
}

# Handles input to dictate wether all tests should be ran, or just one set
function run_tests {
  if [[ "$target" == "all" ]]; then
    echo "Running all tests..."
    for test_dir in "${test_directories[@]}"; do
      run_test "${test_dir}"
    done
    for test_dir in "${role_directories[@]}"; do
      run_role_test "${test_dir}"
    done
    exit 0
  else
    for test_dir in "${test_directories[@]}"; do
      if [[ "$target" == "$test_dir" ]]; then
        run_test "$target"
        exit 0
      fi
    done
    for test_dir in "${role_directories[@]}"; do
      if [[ ${target} == "${test_dir}" ]]; then
        run_role_test ${target}
        exit 0
      fi
      echo "Error: unrecognized test directory given: ${target}"
      echo ""
      help
    done
  fi
}

# Exit if no input given
if [[ $# -eq 0 ]] ; then
  echo "Error: No test directory or flag given"
  echo ""
  help
  exit 1
fi

while getopts adehp:t:v: option; do
  case "$option" in
    a) target='all' ;;
    d) start_dev_env="false" ;;
    e) flags="$flags -e" ;;
    h) help && exit 0 ;;
    p) flags="$flags -p ${OPTARG}" ;;
    t) target="${OPTARG}" ;;
    v) flags="$flags -v ${OPTARG}" ;;
    *)
        echo "$1 is not a valid option"
        help
        exit 1 ;;
  esac
done

function main {
  if [[ "$start_dev_env" == "true" ]]; then
    pushd "$(dev_dir)"
      # shellcheck disable=SC2046
      ./start.sh $(echo "$flags" | cut -c 1-)
    popd
  fi

  run_tests
}

main
