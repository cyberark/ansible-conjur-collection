#!/bin/bash

set -euo pipefail

echo "Running Ansible Lint"
docker run --rm -v "$(pwd)":/work -w /work pipelinecomponents/ansible-lint
echo

echo "Running Pylint"
docker run --rm -v "$(pwd)":/work -w /work python:3 bash -c "pip install pylint && pylint ./plugins/lookup"
echo
