# (c) 2020 CyberArk Software Ltd. All rights reserved.
# (c) 2018 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os.path
import socket
from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase
from cyberark.ansible_conjur_collection.plugins.lookup.conjur_variable import LookupModule
from base64 import b64encode
from netrc import netrc
from os import environ
from time import time, sleep
from ansible.module_utils.six.moves.urllib.parse import quote
from ansible.module_utils.urls import urllib_error
from stat import S_IRUSR, S_IWUSR
from tempfile import gettempdir, NamedTemporaryFile
import yaml

from ansible.module_utils.urls import open_url
from ansible.utils.display import Display
import ssl

MOCK_ENTRIES = [{'CONJUR_APPLIANCE_URL': [os.environ['https://conjur-https']],
                 'CONJUR_ACCOUNT': [os.environ['cucumber']],
                 'CONJUR_AUTHN_LOGIN': [os.environ['host/ansible/ansible-master']],
                 'CONJUR_AUTHN_API_KEY': [os.environ['ANSIBLE_MASTER_AUTHN_API_KEY']],
                 'COMPOSE_PROJECT_NAME': [os.environ['COMPOSE_PROJECT_NAME']]}]

# MOCK_ENTRIES = [{'username': 'user',
#                  'name': 'Mock Entry',
#                  'password': 't0pS3cret passphrase entry!',
#                  'url': 'https://localhost/login',
#                  'notes': 'Test\nnote with multiple lines.\n',
#                  'id': '0123456789'}]

class MockLPass(LookupModule):
    _mock_logged_out = False
    _mock_disconnected = False

class DisconnectedMockLPass(LookupModule):

    _mock_disconnected = True

class LoggedOutMockLPass(LookupModule):

    _mock_logged_out = True
