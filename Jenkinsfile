# This file implements a Github action to run Ansible collection sanity tests
# on the Conjur Ansible Collection. The Ansible collection sanity tests are
# run across the following matrices:
#
#Ansible versions:
#    - stable-2.9
#    - stable-2.10
#    - devel
#
#Python versions:
#    - Python 3.8

name: CI
on:
# Run CI against all pushes (direct commits) and Pull Requests
- push
- pull_request

jobs:

###
# Sanity tests (REQUIRED)
#
# https://docs.ansible.com/ansible/latest/dev_guide/testing_sanity.html

  sanity:
    name: Sanity (${{ matrix.ansible }}+py${{ matrix.python }})
    strategy:
      matrix:
        ansible:
          # It's important that Sanity is tested against all stable-X.Y branches
          # Testing against `devel` may fail as new tests are added.
          - stable-2.9
          - stable-2.10
          - stable-2.11
          - stable-2.12
          - devel
        python:
          - 3.8
    runs-on: ubuntu-latest
    steps:

      # ansible-test requires the collection to be in a directory in the form
      # .../ansible_collections/cyberark/conjur/

      - name: Check out code
        uses: actions/checkout@v2
        with:
          path: ansible_collections/cyberark/conjur

      - name: Set up Python ${{ matrix.ansible }}
        uses: actions/setup-python@v2
        with:
          python-version: ${{ matrix.python }}

      # Install the head of the given branch (devel, stable-2.10)
      - name: Install ansible-base (${{ matrix.ansible }})
        run: pip install https://github.com/ansible/ansible/archive/${{ matrix.ansible }}.tar.gz --disable-pip-version-check

      # run ansible-test sanity inside of Docker.
      # The docker container has all the pinned dependencies that are required.
      # Explicity specify the version of Python we want to test
      - name: Run sanity tests
        run: ansible-test sanity --docker -v --color --python ${{ matrix.python }}
        working-directory: ./ansible_collections/cyberark/conjur


# Unit tests (OPTIONAL)

# https://docs.ansible.com/ansible/latest/dev_guide/testing_units.html

  units:
    runs-on: ubuntu-latest
    name: Units (Ⓐ${{ matrix.ansible }}+py${{ matrix.python }})
    strategy:
      # As soon as the first unit test fails, cancel the others to free up the CI queue
      fail-fast: true
      matrix:
        ansible:
          # - stable-2.9 # Only if your collection supports Ansible 2.9
          - stable-2.10
          - devel
        python:
          - 3.8
        exclude:
          - ansible: stable-2.9
            python: 3.9

    steps:
      - name: Check out code
        uses: actions/checkout@v2
        with:
          path: ansible_collections/cyberark/conjur

      - name: Set up Python ${{ matrix.ansible }}
        uses: actions/setup-python@v2
        with:
          python-version: ${{ matrix.python }}

      - name: Install ansible-base (${{ matrix.ansible }})
        run: pip install https://github.com/ansible/ansible/archive/${{ matrix.ansible }}.tar.gz --disable-pip-version-check

      # Run the unit tests
      - name: Run unit test
        run: ansible-test units --docker default -v --python ${{ matrix.python }}
        working-directory: ./ansible_collections/cyberark/conjur

      # ansible-test support producing code coverage date
      - name: Generate coverage report
        run: ansible-test coverage xml -v --requirements --group-by command --group-by version
        working-directory: ./ansible_collections/cyberark/conjur

      # See the reports at https://codecov.io/gh/GITHUBORG/REPONAME
      - uses: codecov/codecov-action@v2
        with:
          fail_ci_if_error: false
