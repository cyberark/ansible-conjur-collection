# (c) 2018, Jason Vanderhoof <jason.vanderhoof@cyberark.com>, Oren Ben Meir <oren.benmeir@cyberark.com>
# (c) 2018 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = """
    lookup: conjur_variable
    version_added: "2.5"
    short_description: Fetch credentials from CyberArk Conjur.
    description:
      - Retrieves credentials from Conjur using the controlling host's Conjur identity
        or environment variables.
      - Environment variables could be CONJUR_ACCOUNT, CONJUR_APPLIANCE_URL, CONJUR_CERT_FILE, CONJUR_AUTHN_LOGIN, CONJUR_AUTHN_API_KEY
      - Conjur info: U(https://www.conjur.org/).
    requirements:
      - 'The controlling host running Ansible has a Conjur identity. (More: U(https://docs.conjur.org/latest/en/Content/Get%20Started/key_concepts/machine_identity.html))'
    options:
      _term:
        description: Variable path
        required: True
      identity_file:
        description: Path to the Conjur identity file. The identity file follows the netrc file format convention.
        type: path
        default: /etc/conjur.identity
        required: False
        ini:
          - section: conjur,
            key: identity_file_path
        env:
          - name: CONJUR_IDENTITY_FILE
      config_file:
        description: Path to the Conjur configuration file. The configuration file is a YAML file.
        type: path
        default: /etc/conjur.conf
        required: False
        ini:
          - section: conjur,
            key: config_file_path
        env:
          - name: CONJUR_CONFIG_FILE
"""

EXAMPLES = """
  - debug:
      msg: "{{ lookup('conjur_variable', '/path/to/secret') }}"
"""

RETURN = """
  _raw:
    description:
      - Value stored in Conjur.
"""

import os.path
from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase
from base64 import b64encode
from netrc import netrc
from os import environ
from time import time
from ansible.module_utils.six.moves.urllib.parse import quote_plus
import yaml

from ansible.module_utils.urls import open_url
from ansible.utils.display import Display

display = Display()


# Load configuration and return as dictionary if file is present on file system
def _load_conf_from_file(conf_path):
    display.vvv('conf file: {0}'.format(conf_path))

    if not os.path.exists(conf_path):
        return {}
        # raise AnsibleError('Conjur configuration file `{0}` was not found on the controlling host'
        #                    .format(conf_path))

    display.vvvv('Loading configuration from: {0}'.format(conf_path))
    with open(conf_path) as f:
        config = yaml.safe_load(f.read())
        return config


# Load identity and return as dictionary if file is present on file system
def _load_identity_from_file(identity_path, appliance_url):
    display.vvvv('identity file: {0}'.format(identity_path))

    if not os.path.exists(identity_path):
        return {}
        # raise AnsibleError('Conjur identity file `{0}` was not found on the controlling host'
        #                    .format(identity_path))

    display.vvvv('Loading identity from: {0} for {1}'.format(identity_path, appliance_url))

    conjur_authn_url = '{0}/authn'.format(appliance_url)
    identity = netrc(identity_path)

    if identity.authenticators(conjur_authn_url) is None:
        raise AnsibleError('The netrc file on the controlling host does not contain an entry for: {0}'
                           .format(conjur_authn_url))

    id, account, api_key = identity.authenticators(conjur_authn_url)
    if not id or not api_key:
        return {}

    return {'id': id, 'api_key': api_key}

# Merge multiple dictionaries by using dict.update mechanism
def _merge_dictionaries(*arg):
    ret = {}
    for a in arg:
        ret.update(a)
    return ret

# Use credentials to retrieve temporary authorization token
def _fetch_conjur_token(conjur_url, account, username, api_key):
    conjur_url = '{0}/authn/{1}/{2}/authenticate'.format(conjur_url, account, quote_plus(username))
    display.vvvv('Authentication request to Conjur at: {0}, with user: {1}'.format(conjur_url, quote_plus(username)))

    response = open_url(conjur_url, data=api_key, method='POST')
    code = response.getcode()
    if code != 200:
        raise AnsibleError('Failed to authenticate as \'{0}\' (got {1} response)'
                           .format(username, code))

    return response.read()


# Retrieve Conjur variable using the temporary token
def _fetch_conjur_variable(conjur_variable, token, conjur_url, account):
    token = b64encode(token)
    headers = {'Authorization': 'Token token="{0}"'.format(token.decode("utf-8"))}
    display.vvvv('Header: {0}'.format(headers))

    url = '{0}/secrets/{1}/variable/{2}'.format(conjur_url, account, quote_plus(conjur_variable))
    display.vvvv('Conjur Variable URL: {0}'.format(url))

    response = open_url(url, headers=headers, method='GET')

    if response.getcode() == 200:
        display.vvvv('Conjur variable {0} was successfully retrieved'.format(conjur_variable))
        return [response.read().decode("utf-8")]
    if response.getcode() == 401:
        raise AnsibleError('Conjur request has invalid authorization credentials')
    if response.getcode() == 403:
        raise AnsibleError('The controlling host\'s Conjur identity does not have authorization to retrieve {0}'
                           .format(conjur_variable))
    if response.getcode() == 404:
        raise AnsibleError('The variable {0} does not exist'.format(conjur_variable))

    return {}


class LookupModule(LookupBase):

    def run(self, terms, variables=None, **kwargs):
        conf_file = self.get_option('config_file')
        conf = _merge_dictionaries(
            _load_conf_from_file(conf_file),
            {
                "account": environ.get('CONJUR_ACCOUNT'),
                "appliance_url": environ.get("CONJUR_APPLIANCE_URL")
            } if (
                  environ.get('CONJUR_ACCOUNT') is not None
                  and environ.get('CONJUR_APPLIANCE_URL') is not None
              )
            else {},
            {
                "cert_file": environ.get('CONJUR_CERT_FILE')
            } if (environ.get('CONJUR_CERT_FILE') is not None)
            else {}
        )

        identity_file = self.get_option('identity_file')
        identity = _merge_dictionaries(
            _load_identity_from_file(identity_file, conf['appliance_url']),
            {
                "id": environ.get('CONJUR_AUTHN_LOGIN'),
                "api_key": environ.get('CONJUR_AUTHN_API_KEY')
            } if (environ.get('CONJUR_AUTHN_LOGIN') is not None
                  and environ.get('CONJUR_AUTHN_API_KEY') is not None)
            else {}
        )

        if 'account' not in conf or 'appliance_url' not in conf:
            raise AnsibleError(
                        ("Configuration file on the controlling host must "
                         "define `account` and `appliance_url`"
                         "entries or they should be environment variables")
            )

        if 'id' not in identity or 'api_key' not in identity:
            raise AnsibleError(
                        ("Identity file on the controlling host must contain "
                         "`login` and `password` entries for Conjur appliance"
                         " URL or they should be environment variables")
            )

        token = _fetch_conjur_token(
                    conf['appliance_url'],
                    conf['account'],
                    identity['id'],
                    identity['api_key']
                )
        return _fetch_conjur_variable(
                    terms[0],
                    token,
                    conf['appliance_url'],
                    conf['account']
                )
