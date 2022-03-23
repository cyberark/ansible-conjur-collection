# (c) 2020 CyberArk Software Ltd. All rights reserved.
# (c) 2018 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os.path
import socket
from base64 import b64encode
from netrc import netrc
from os import environ
from time import time, sleep
import ssl

MOCK_ENTRIES = [{'CONJUR_APPLIANCE_URL': [os.environ['https://conjur-https']],
                 'CONJUR_ACCOUNT': [os.environ['cucumber']],
                 'CONJUR_AUTHN_LOGIN': [os.environ['host/ansible/ansible-master']],
                 'CONJUR_AUTHN_API_KEY': [os.environ['ANSIBLE_MASTER_AUTHN_API_KEY']],
                 'COMPOSE_PROJECT_NAME': [os.environ['COMPOSE_PROJECT_NAME'] + '_ansible_1']}]
print(" MOCK_ENTRIES ")
print(MOCK_ENTRIES)
