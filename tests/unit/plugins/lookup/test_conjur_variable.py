# -*- coding: utf-8 -*-
# (c) 2020, Adam Migus <adam@migus.org>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# Make coding more python3-ish
from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.cyberark.conjur.tests.unit.compat.unittest import TestCase
from ansible_collections.cyberark.conjur.tests.unit.compat.mock import (
    patch,
    MagicMock,
)
from ansible_collections.cyberark.conjur.plugins.lookup import conjur_variable
from ansible.plugins.loader import lookup_loader

class MockSecretsVault(MagicMock):
    RESPONSE = '{"foo": "bar"}'

    def get_secret_json(self, path):
        return self.RESPONSE


class TestLookupModule(TestCase):
    def setUp(self):
        self.lookup = lookup_loader.get("ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable")

    @patch(
        "ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_variable",
        MockSecretsVault(),
    )
    def test_get_secret_json(self):
        self.assertListEqual(
            [MockSecretsVault.RESPONSE],
            self.lookup.run(
                ["/dummy"],
                [],
                **{"terms[0]": "dummy", "token": "dummy", "conf['appliance_url']": "dummy", "conf['account']": "dummy", "validate_certs": "dummy", "cert_file": "dummy", }
            ),
        )
