#!/bin/bash -eu

export DOCKER_BUILDKIT=1

ansible_version="2.17"
python_version="3.12"
gen_report="false"

cd "$(dirname "$0")"/..

function print_usage() {
   cat << EOF
Run unit tests for Conjur Variable Lookup plugin.

./ansibletest.sh [options]

-a <version>     Run tests against specified Ansible version (Default: 2.17)
-p <version>     Run tests against specified Python version  (Default: 3.12)
-r               Generate test coverage report
EOF
}

while getopts 'a:p:r' flag; do
  case "${flag}" in
    a) ansible_version="${OPTARG}" ;;
    p) python_version="${OPTARG}" ;;
    r) gen_report="true" ;;
    *) print_usage
       exit 1 ;;
   esac
done

if [[ -n "${PIP_CONF:-}" ]]; then
  pip_secret="id=pip_conf,env=PIP_CONF"
elif [[ -f "${HOME}/.pip/pip.conf" ]] && grep -q "jfrog.io" "${HOME}/.pip/pip.conf"; then
  pip_secret="id=pip_conf,src=${HOME}/.pip/pip.conf"
else
  echo "ERROR: Artifactory credentials not available." >&2
  echo "Either set the PIP_CONF env var or configure ~/.pip/pip.conf with jfrog.io credentials." >&2
  exit 1
fi

test_cmd="ansible-test units -v --python $python_version"
if [[ "$gen_report" == "true" ]]; then
  test_cmd="ansible-test coverage erase;
    $test_cmd --coverage;
    ansible-test coverage xml --requirements --group-by command;
  "
fi

docker build \
  --secret "${pip_secret}" \
  --build-arg PYTHON_VERSION="${python_version}" \
  --build-arg ANSIBLE_VERSION="${ansible_version}" \
  -t pytest-tools:latest \
  -f tests/unit/Dockerfile .
docker run --rm \
  -v "${PWD}/":/ansible_collections/cyberark/conjur/ \
  -w /ansible_collections/cyberark/conjur/tests/unit/ \
  pytest-tools:latest /bin/bash -c "
    git config --global --add safe.directory /ansible_collections/cyberark/conjur
    git config --global --add safe.directory /ansible_collections/cyberark/conjur/dev/conjur-intro
    $test_cmd
  "
