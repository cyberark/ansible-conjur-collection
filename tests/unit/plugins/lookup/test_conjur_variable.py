# -*- coding: utf-8 -*-
# (c) 2020, Adam Migus <adam@migus.org>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# Make coding more python3-ish
from __future__ import absolute_import, division, print_function

__metaclass__ = type

from cyberark.ansible_conjur_collection.tests.unit.compat.unittest import TestCase
from cyberark.ansible_conjur_collection.tests.unit.compat.mock import (
    patch,
    MagicMock,
)
from cyberark.ansible_conjur_collection.plugins.lookup import conjur_variable
from ansible.plugins.loader import lookup_loader


class MockSecretsVault(MagicMock):
    RESPONSE = '{"foo": "bar"}'

    def get_secret_json(self, path):
        return self.RESPONSE


class TestLookupModule(TestCase):
    def setUp(self):
        self.lookup = lookup_loader.get("cyberark.ansible_conjur_collection.conjur_variable")

    @patch(
        "cyberark.ansible_conjur_collection.plugins.lookup.conjur_variable.LookupModule",
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