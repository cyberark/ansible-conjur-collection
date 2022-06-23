#!/bin/bash
set -ex


conjur_oss="false"
conjur_enterprise="false"

function print_usage() {
   cat << EOF
Run tests cases for Conjur environments

-s               Run conjur oss
-e               Run conjur enterprise
EOF
}

while getopts 's:e' flag; do
  case "${flag}" in
    s) conjur_oss="true" ;;
    e) conjur_enterprise="true" ;;
    *) print_usage
       exit 1 ;;
   esac
done

# if [[ "$conjur_oss" == "true" ]]; then
#  ./start_oss.sh
# fi

# if [[ "$conjur_enterprise" == "true" ]]; then
# pushd ../tests/conjur_variable
# ./start_enterprise.sh
# popd
# fi

if [[  "$conjur_oss" == "true" ]]
then
 echo " Just for testing"
elif [[ "$conjur_enterprise" == "true" ]]
then
  pushd ../tests/conjur_variable
  ./testing.sh
  rm -rf conjur-intro
  popd
else
  echo "You are not giving correct inputs."
  exit 1;
fi