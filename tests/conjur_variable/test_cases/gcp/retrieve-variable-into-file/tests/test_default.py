from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import os

testinfra_hosts = [os.environ['COMPOSE_PROJECT_NAME'] + '-ansible-1']


def test_retrieved_secret(host):
    """
    Verify that the as_file parameter makes the lookup plugin return the path to a temporary file
    containing the secret. Mode and content are captured by the playbook itself, right after the
    lookup runs, since the temp file's lifetime past that point is not guaranteed (the lookup
    plugin registers a best-effort atexit cleanup for it).
    """
    mode_file = host.file('/conjur_secret_mode.txt')
    content_file = host.file('/conjur_secret_content.txt')
    assert mode_file.exists
    assert content_file.exists
    assert mode_file.content_string.strip() == '600'
    assert content_file.content_string == "test_secret_in_file_password"
