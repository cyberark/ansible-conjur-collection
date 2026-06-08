from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os


testinfra_hosts = [os.environ['COMPOSE_PROJECT_NAME'] + '-ansible-1']


def test_retrieved_secret_via_embedded_oidc(host):
    """Conjur must return the correct secret when authenticated via a JWT
    signed by the embedded OIDC provider and validated through jwks-uri."""
    secrets_file = host.file('/conjur_secrets.txt')

    assert secrets_file.exists

    result = host.check_output("cat /conjur_secrets.txt", shell=True)

    assert result == "test_secret_password"
