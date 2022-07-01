#!/bin/bash -eu

./dev/test_unit.sh -a stable-2.10 -p 3.8

ansible-test sanity --docker -v --color --python 3.8

