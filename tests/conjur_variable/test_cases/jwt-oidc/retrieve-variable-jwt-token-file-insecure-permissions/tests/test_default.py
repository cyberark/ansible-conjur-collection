from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os


testinfra_hosts = [os.environ['COMPOSE_PROJECT_NAME'] + '-ansible-1']


def test_retrieves_secret_despite_insecure_permissions(host):
    """conjur_authn_jwt_token_file only warns (does not fail) on insecure
    file permissions, so the secret must still be retrieved successfully."""
    secrets_file = host.file('/conjur_secrets.txt')

    assert secrets_file.exists

    result = host.check_output("cat /conjur_secrets.txt", shell=True)

    assert result == "test_secret_password"


def test_insecure_permissions_warning_is_logged(host):
    """The plugin must warn about the insecure token file permissions."""
    log_file = host.file(
        '/tmp/ansible-playbook-retrieve-variable-jwt-token-file-insecure-permissions.log'
    )

    assert log_file.exists

    log_contents = log_file.content_string

    # Ansible wraps long [WARNING] lines at the terminal width, so the
    # message may be split across a newline (e.g. "insecure\npermissions").
    normalized_log_contents = " ".join(log_contents.split())

    assert "insecure permissions" in normalized_log_contents
