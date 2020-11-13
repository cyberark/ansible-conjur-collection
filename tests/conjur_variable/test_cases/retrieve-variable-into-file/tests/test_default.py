from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import os
import testinfra.utils.ansible_runner

testinfra_hosts = [os.environ['COMPOSE_PROJECT_NAME'] + '_ansible_1']


def test_retrieved_secret(host):
    secret_path_file = host.file('/conjur_secret_path.txt')
    assert secret_path_file.exists

    secret_path = host.check_output("cat /conjur_secret_path.txt", shell=True)
    secret_file = host.file(secret_path)
    assert secret_file.exists
    assert secret_file.mode == 0o600

    secret = host.check_output("cat {0}".format(secret_path), shell=True)
    assert secret == "test_secret_in_file_password"
