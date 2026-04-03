from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os


testinfra_hosts = [os.environ['COMPOSE_PROJECT_NAME'] + '-ansible-1']


def test_missing_service_id_raises_error(host):
    """The plugin must raise an AnsibleError when conjur_authn_service_id is absent
    and authn_type is set to 'authn-cert'."""
    secrets_file = host.file('/conjur_secrets.txt')

    assert secrets_file.exists

    result = host.check_output("cat /conjur_secrets.txt", shell=True)

    # Playbook records "error_raised" when the lookup fails as expected
    assert result == "error_raised"
