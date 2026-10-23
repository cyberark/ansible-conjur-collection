#!/bin/bash

set -euo pipefail

echo "Running Ansible Lint"
# Hide pip.conf: this container mounts the repo root but does not need registry credentials.
docker run --rm \
  -v "$(pwd)":/work \
  -v /dev/null:/work/pip.conf:ro \
  -w /work pipelinecomponents/ansible-lint
echo

echo "Running Pylint"
SECRET_ARGS=()
[ -f pip.conf ] && SECRET_ARGS+=(--secret id=pip_conf,src=pip.conf)
DOCKER_BUILDKIT=1 docker build \
  "${SECRET_ARGS[@]+"${SECRET_ARGS[@]}"}" \
  --no-cache \
  -t pylint-tools:latest \
  -f - . << 'EOF'
# syntax=docker/dockerfile:1
FROM python:3.12@sha256:17b9724493d916f56565c131f389faff2597f46dec6ce09516f95125bc9f519f
RUN --mount=type=secret,id=pip_conf,target=/root/.pip/pip.conf,required=false \
    pip install pylint
EOF
docker run --rm \
  -v "$(pwd)":/work \
  -v /dev/null:/work/pip.conf:ro \
  -w /work \
  pylint-tools:latest pylint ./plugins/lookup
echo
