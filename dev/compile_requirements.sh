#!/bin/bash -eu

cd "$(dirname "$0")/.."

source dev/util.sh
require_pip_conf

PIP_TOOLS_VERSION="7.6.2"

# Table of all managed lockfiles: work_dir|in_name|out_name|py_ver
# work_dir is relative to the repo root and is mounted at /work inside the container.
# Each file's own folder is used as the mount so the generated headers are byte-identical.
LOCKFILES=(
  "tests/unit|requirements.in|requirements.txt|3.12"
  "dev/oidc-provider|requirements.in|requirements.txt|3.12"
  "tests|requirements-ansible-core-2.17.in|requirements-ansible-core-2.17.txt|3.12"
  "tests|requirements-ansible-core-2.18.in|requirements-ansible-core-2.18.txt|3.13"
  "tests|requirements-ansible-core-2.19.in|requirements-ansible-core-2.19.txt|3.13"
  "dev|requirements-ansible-11.in|requirements-ansible-11.txt|3.12"
  "dev|requirements-ansible-12.in|requirements-ansible-12.txt|3.12"
  "ci|requirements-build.in|requirements-build.txt|3.12"
  "ci|requirements-publish.in|requirements-publish.txt|3.12"
)

compile_lockfile() {
  local work_dir="$1" in_name="$2" out_name="$3" py_ver="$4"
  echo "Compiling ${work_dir}/${out_name} (python:${py_ver}-slim)..."
  # Use docker build with a BuildKit secret so pip.conf is only visible during the
  # RUN step and is never stored in an image layer or accessible after pip exits.
  # --output type=local extracts the compiled .txt file back to the host work_dir.
  DOCKER_BUILDKIT=1 docker build \
    --secret id=pip_conf,src="${PIP_CONF}" \
    --no-cache \
    --output "type=local,dest=$(pwd)/${work_dir}" \
    -f - "$(pwd)/${work_dir}" << EOF
# syntax=docker/dockerfile:1
FROM python:${py_ver}-slim AS compile
COPY . /work/
RUN --mount=type=secret,id=pip_conf,target=/root/.pip/pip.conf \
    pip install pip-tools==${PIP_TOOLS_VERSION} && \
    pip-compile --generate-hashes --no-emit-index-url \
      --output-file /work/${out_name} /work/${in_name}
FROM scratch
COPY --from=compile /work/${out_name} /${out_name}
EOF
}

if [[ $# -eq 0 ]]; then
  # No arguments: compile all lockfiles.
  for entry in "${LOCKFILES[@]}"; do
    IFS='|' read -r work_dir in_name out_name py_ver <<< "$entry"
    compile_lockfile "$work_dir" "$in_name" "$out_name" "$py_ver"
  done
else
  # Arguments are .in file paths relative to the repo root (e.g. tests/unit/requirements.in).
  for target in "$@"; do
    matched=0
    for entry in "${LOCKFILES[@]}"; do
      IFS='|' read -r work_dir in_name out_name py_ver <<< "$entry"
      if [[ "${work_dir}/${in_name}" == "$target" ]]; then
        compile_lockfile "$work_dir" "$in_name" "$out_name" "$py_ver"
        matched=1
        break
      fi
    done
    if [[ "$matched" -eq 0 ]]; then
      echo "ERROR: No lockfile entry for '${target}'." >&2
      echo "Known .in paths:" >&2
      for entry in "${LOCKFILES[@]}"; do
        IFS='|' read -r work_dir in_name _ _ <<< "$entry"
        echo "  ${work_dir}/${in_name}" >&2
      done
      exit 1
    fi
  done
fi

echo "Done."
