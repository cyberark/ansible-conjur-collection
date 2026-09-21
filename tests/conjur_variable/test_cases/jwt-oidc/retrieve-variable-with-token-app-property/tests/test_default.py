from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os


testinfra_hosts = [os.environ['COMPOSE_PROJECT_NAME'] + '-ansible-1']


def test_retrieved_secret_via_token_app_property(host):
    """Conjur must return the correct secret when identity is resolved purely
    from the JWT's 'sub' claim (token-app-property mode), with no host_id in
    the authentication URL."""
    secrets_file = host.file('/conjur_secrets.txt')

    assert secrets_file.exists

    result = host.check_output("cat /conjur_secrets.txt", shell=True)

    assert result == "test_secret_password"
