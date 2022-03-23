# (c) 2020 CyberArk Software Ltd. All rights reserved.
# (c) 2018 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os.path
import socket
from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase
from cyberark.ansible_conjur_collection.plugins.lookup import LookupModule, LPass, LPassException
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

class MockLPass(LPass):
    _mock_logged_out = False
    _mock_disconnected = False


class DisconnectedMockLPass(MockLPass):

    _mock_disconnected = True


class LoggedOutMockLPass(MockLPass):

    _mock_logged_out = True
