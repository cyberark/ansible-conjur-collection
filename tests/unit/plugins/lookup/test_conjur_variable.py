from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.cyberark.conjur.tests.unit.compat.unittest import TestCase
from ansible_collections.cyberark.conjur.tests.unit.compat.mock import patch, MagicMock
from ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable import _merge_dictionaries
from ansible.plugins.loader import lookup_loader


class MockSecretsVault(MagicMock):
    RESPONSE = {'id': 'host/ansible/ansible-master', 'api_key': '1j8t1rx2ghwhx7392wt1h14qn3c22yp4w2y395yk9d2hz8gvb1nbh6yg'}

    def get_secret_json(self, path):
        return self.RESPONSE


class Test(TestCase):
    def setUp(self):
        self.lookup = lookup_loader.get("plugins.lookup.conjur_variable")

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._merge_dictionaries', MockSecretsVault())
    def test_get_secret_json(self):
        functionOutput = _merge_dictionaries(
            {},
            {'id': 'host/ansible/ansible-master', 'api_key': '1j8t1rx2ghwhx7392wt1h14qn3c22yp4w2y395yk9d2hz8gvb1nbh6yg'}
        )
        self.assertEquals(MockSecretsVault.RESPONSE, functionOutput)
