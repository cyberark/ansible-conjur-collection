#!/bin/bash
set -ex
source "$(git rev-parse --show-toplevel)/dev/util.sh"

declare -x DOCKER_NETWORK='default'

echo "---- removing dev environment----"
cd "$(dev_dir)"

docker compose down -v

if [[ -n "$(cli_cid)" ]]; then
  docker rm -f "$(cli_cid)" 2>/dev/null
fi

if [ -d "conjur-intro" ] && [ "$(ls -A conjur-intro)" ]; then
  pushd conjur-intro > /dev/null
    ./bin/dap --stop
  popd > /dev/null
fi


clean_submodules

rm -rf inventory.tmp \
       conjur.pem \
       access_token \
       cyberark-conjur-*tar.gz
