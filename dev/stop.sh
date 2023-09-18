#!/bin/bash
set -ex
source "$(git rev-parse --show-toplevel)/dev/util.sh"

declare -x DOCKER_NETWORK='default'

echo "---- removing dev environment----"
cd "$(dev_dir)"

docker-compose down -v

if [[ -n "$(cli_cid)" ]]; then
  docker rm -f "$(cli_cid)"
fi

if [[ -d conjur-intro ]]; then
  pushd conjur-intro
    ./bin/dap --stop
  popd
fi

clean_submodules

rm -rf inventory.tmp \
       conjur.pem \
       access_token
