#!/bin/bash -eu

export DOCKER_BUILDKIT=1

ansible_version="2.19"
python_version="3.13"
gen_report="false"
artifact_file=""

cd "$(dirname "$0")"/..

function print_usage() {
   cat << EOF
Run sanity tests for Conjur Variable Lookup plugin.

./dev/test_sanity.sh [options]

-a <version>     Run tests against specified Ansible version (Default: 2.19)
-p <version>     Run tests against specified Python version  (Default: 3.13)
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

if [[ "$ansible_version" == stable-* ]]; then
  echo "ERROR: Pass the bare version number (e.g. '2.19')." >&2
  exit 1
fi

collection_root="$(pwd)"

# Find the artifact in the current directory
artifact_file=$(ls cyberark-conjur-*.tar.gz 2>/dev/null || true)

# Point to extracted artifact directory if available
if [[ -n "$artifact_file" ]]; then
  EXTRACT_DIR="$(pwd)/build/collection"
  mkdir -p "$EXTRACT_DIR"
  echo "Using artifact: $artifact_file"
  echo "Extracting collection artifact: $artifact_file"
  tar -xzf "$artifact_file" -C "$EXTRACT_DIR"
  collection_root="$EXTRACT_DIR"
else
  echo "No artifact found in repo root. Running against source folder."
fi

test_cmd="ansible-test sanity -v --color --python $python_version"

# Only add excludes if the files actually exist (i.e. not running against an artifact file)
for path in dev/ ci/ secrets.yml Jenkinsfile; do
  if [[ -e "$collection_root/$path"  ]]; then
    test_cmd+=" --exclude $path"
  fi
done

if [[ "$gen_report" == "true" ]]; then
  test_cmd="ansible-test coverage erase;
    $test_cmd --coverage;
    ansible-test coverage html --requirements --group-by command;
  "
fi

source dev/util.sh
require_pip_conf
pip_secret="id=pip_conf,src=${PIP_CONF}"

# In source mode the repo root is mounted, which includes pip.conf.
# Shadow it so the test container cannot read registry credentials.
pip_conf_shadow=()
if [[ -z "$artifact_file" ]]; then
  pip_conf_shadow=(-v /dev/null:/ansible_collections/cyberark/conjur/pip.conf:ro)
fi

docker build \
  --secret "${pip_secret}" \
  --build-arg PYTHON_VERSION="${python_version}" \
  --build-arg ANSIBLE_VERSION="${ansible_version}" \
  -t "pytest-tools:${ansible_version}" \
  -f tests/sanity/Dockerfile .
docker run --rm \
  "${pip_conf_shadow[@]}" \
  -v "${collection_root}":/ansible_collections/cyberark/conjur/ \
  -v "$(pwd)/tests/output/reports":/ansible_collections/cyberark/conjur/tests/output/reports \
  -w /ansible_collections/cyberark/conjur/ \
  "pytest-tools:${ansible_version}" /bin/bash -c "
    git config --global --add safe.directory /ansible_collections/cyberark/conjur
    git config --global --add safe.directory /ansible_collections/cyberark/conjur/dev/conjur-intro
    $test_cmd
  "

if [[ -n "$artifact_file" ]]; then
  echo "Sanity tests completed against artifact: $artifact_file"
else
  echo "Sanity tests completed against source folder. It is recommended to run against an artifact generated via 'ci/build_release'"
fi

