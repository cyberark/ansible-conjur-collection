from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os


testinfra_hosts = [os.environ['COMPOSE_PROJECT_NAME'] + '-ansible-1']


def test_retrieved_secret_via_jwt_token_file(host):
    """Conjur must return the correct secret when the JWT is supplied via
    conjur_authn_jwt_token_file rather than conjur_authn_jwt_token."""
    secrets_file = host.file('/conjur_secrets.txt')

    assert secrets_file.exists

    result = host.check_output("cat /conjur_secrets.txt", shell=True)

    assert result == "test_secret_password"
