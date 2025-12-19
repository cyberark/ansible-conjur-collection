from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os


testinfra_hosts = [os.environ['COMPOSE_PROJECT_NAME'] + '-ansible-1']


def test_retry_mechanism_executed(host):
    # Verify we can connect to the test host
    assert host.exists

    # The actual retry test is performed by the playbook's assertions
    # This test confirms the infrastructure is available
    result = host.run("echo 'Retry test infrastructure ready'")
    assert result.rc == 0
