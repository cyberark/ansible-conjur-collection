#!/usr/bin/env bash
source bin/util

# go to root folder for execution
cd $(dirname $0)/..

python_version="3.9"
ansible_version="stable-2.10"

function print_usage() {
   cat << EOF
Run unit tests for Conjur Variable Lookup plugin.

./ansibletest.sh [options]

-p <version>     Run tests against specified Python version  (Default: 3.9)
-a <version>     Run tests against specified Ansible version (Default: stable-2.10)
EOF
}

while getopts 'a:p:' flag; do
  case "${flag}" in
    a) ansible_version="${OPTARG}" ;;
    p) python_version="${OPTARG}" ;;
    *) print_usage
       exit 1 ;;
   esac
done

docker build \
  --build-arg PYTHON_VERSION="${python_version}" \
  --build-arg ANSIBLE_VERSION="${ansible_version}" \
  -t pytest-tools:latest \
  -f tests/unit/Dockerfile .
docker run --rm \
  -v "${PWD}/":/ansible_collections/cyberark/conjur/ \
  -w /ansible_collections/cyberark/conjur/tests/unit/ \
  pytest-tools:latest /bin/bash -c "
    ansible-test units -vvv --coverage --python ${python_version}
    ansible-test coverage html -v --requirements --group-by command --group-by version
  "
