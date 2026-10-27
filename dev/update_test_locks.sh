#!/bin/bash -eu
# Regenerates the hash-pinned lock files used by tests/{sanity,unit}/Dockerfile
# and .github/workflows/ansible-test.yml (pip install --require-hashes).
# Requires uv (https://docs.astral.sh/uv/). Run from anywhere:
#   ./dev/update_test_locks.sh
#
# Each lock = ansible-core for the given matrix entry + tests/unit/requirements.txt.
# "devel" is pinned to the latest stable ansible-core release (no pre-releases,
# per Aegis PY-010), so it acts as a smoke test for the newest release line.

cd "$(dirname "$0")"/../tests/requirements

# matrix name | ansible-core constraint | minimum Python
locks=(
  "stable-2.17|ansible-core==2.17.*|3.10"
  "stable-2.18|ansible-core==2.18.*|3.11"
  "stable-2.19|ansible-core==2.19.*|3.11"
  "devel|ansible-core|3.13"
)

for entry in "${locks[@]}"; do
  IFS='|' read -r name constraint min_python <<< "$entry"
  echo "Generating ansible-${name}.txt (${constraint}, python>=${min_python})"
  { echo "$constraint"; cat ../unit/requirements.txt; } | uv pip compile - \
    --universal \
    --python-version "$min_python" \
    --generate-hashes \
    --no-header \
    --quiet \
    -o "ansible-${name}.txt"
done
