#!/bin/bash -x

# Test runner for Ansible Conjur Collection

# Directories containing a `test.sh` file
test_directories=("conjur" "conjur-host-identity")

# Target directory that can be manually set by passing a value to the `-d` flag
target=""

# Print usage instructions
function help {
    echo "Test runner for Ansible Conjur Collection"

    echo "-a        Run all test files in default test directories"
    echo "-d <arg>  Run test file in given directory. Valid options are: ${test_directories[*]} all"
    echo "-h        View help and available commands"
    exit 1
}

# Run a `test.sh` file in a given subdirectory of the top-level `tests` directory
function run_test {
    pushd "${PWD}/tests/${1}"
        echo "Running tests for ${1}..."
        ./test.sh
    popd
}

# Handles input to dictate wether all tests should be ran, or just one set
function handle_input {
    if [[ ! -z ${target} ]]; then
        for test_dir in "${test_directories[@]}"; do 
            if [[ ${target} == "${test_dir}" ]]; then
                run_test ${target}
                exit 0
            fi
        done
        echo "Error: unrecognized test directory given: ${target}"
        echo ""
        help
    else
        echo "Running all tests..."
        for test_dir in "${test_directories[@]}"; do 
            run_test "${test_dir}"
        done
        exit 0
    fi
}

# Exit if no input given
if [[ $# -eq 0 ]] ; then
    echo "Error: No test directory or flag given"
    echo ""
    help
fi

while getopts ahd: option; do
  case "$option" in
        a) handle_input
            ;;
        d) target=${OPTARG}
            handle_input
            ;;
        h) help
            ;;
    esac
done

