from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest import TestCase
from unittest.mock import MagicMock, patch
from ansible.errors import AnsibleError
from ansible.plugins.loader import lookup_loader

from ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable import _merge_dictionaries, _fetch_conjur_token, _fetch_conjur_variable, \
    _validate_pem_certificate, _load_identity_from_file, _load_conf_from_file


class MockMergeDictionaries(MagicMock):
    RESPONSE = {'id': 'host/ansible/ansible-fake', 'api_key': 'fakekey'}


class MockFileload(MagicMock):
    RESPONSE = {}


class TestConjurLookup(TestCase):
    def setUp(self):
        self.lookup = lookup_loader.get("conjur_variable")

    def test_merge_dictionaries(self):
        functionOutput = _merge_dictionaries(
            {},
            {'id': 'host/ansible/ansible-fake', 'api_key': 'fakekey'}
        )
        self.assertEqual(MockMergeDictionaries.RESPONSE, functionOutput)

    def test_load_identity_from_file(self):
        load_identity = _load_identity_from_file("/etc/conjur.identity", "https://conjur-fake")
        self.assertEqual(MockFileload.RESPONSE, load_identity)

    def test_load_conf_from_file(self):
        load_conf = _load_conf_from_file("/etc/conjur.conf")
        self.assertEqual(MockFileload.RESPONSE, load_conf)

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_fetch_conjur_token(self, mock_open_url):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = "response body"
        mock_open_url.return_value = mock_response
        result = _fetch_conjur_token("url", "account", "username", "api_key", True, "cert_file")
        mock_open_url.assert_called_with("url/authn/account/username/authenticate",
                                         data="api_key",
                                         method="POST",
                                         validate_certs=True,
                                         ca_path="cert_file")
        self.assertEqual("response body", result)

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._repeat_open_url')
    def test_fetch_conjur_variable(self, mock_repeat_open_url):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = "response body".encode("utf-8")
        mock_repeat_open_url.return_value = mock_response
        result = _fetch_conjur_variable("variable", b'{"protected":"fakeid"}', "url", "account", True, "cert_file")
        mock_repeat_open_url.assert_called_with("url/secrets/account/variable/variable",
                                                headers={'Authorization': 'Token token="eyJwcm90ZWN0ZWQiOiJmYWtlaWQifQ=="'},
                                                method="GET",
                                                validate_certs=True,
                                                ca_path="cert_file")
        self.assertEqual(['response body'], result)

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_certificate_file')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_variable')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_token')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._merge_dictionaries')
    def test_run(self, mock_merge_dictionaries, mock_fetch_conjur_token, mock_fetch_conjur_variable, mock_get_certificate_file):
        mock_get_certificate_file.return_value = "./conjur.pem"
        mock_fetch_conjur_token.return_value = "token"
        mock_fetch_conjur_variable.return_value = ["conjur_variable"]
        mock_merge_dictionaries.side_effect = [
            {'account': 'fakeaccount', 'appliance_url': 'https://conjur-fake', 'cert_file': './conjurfake.pem'},
            {'id': 'host/ansible/ansible-fake', 'api_key': 'fakekey'}
        ]

        terms = ['ansible/fake-secret']
        kwargs = {'as_file': False, 'conf_file': 'conf_file', 'validate_certs': False}
        result = self.lookup.run(terms, **kwargs)

        self.assertEqual(result, ["conjur_variable"])

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_certificate_file')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_variable')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_token')
    def test_run_with_ansible_vars(self, mock_fetch_conjur_token, mock_fetch_conjur_variable, mock_get_certificate_file):
        mock_get_certificate_file.return_value = "./conjur.pem"
        mock_fetch_conjur_token.return_value = "token"
        mock_fetch_conjur_variable.return_value = ["conjur_variable"]

        variables = {'conjur_account': 'fakeaccount',
                     'conjur_appliance_url': 'https://conjur-fake',
                     'conjur_cert_file': './conjurfake.pem',
                     'conjur_authn_login': 'host/ansible/ansible-fake',
                     'conjur_authn_api_key': 'fakekey'}
        terms = ['ansible/fake-secret']

        output = self.lookup.run(terms, variables)
        self.assertEqual(output, ["conjur_variable"])

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_certificate_file')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_variable')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_token')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._merge_dictionaries')
    def test_retrieve_to_file(self, mock_merge_dictionaries, mock_fetch_conjur_token, mock_fetch_conjur_variable, mock_get_certificate_file):
        mock_get_certificate_file.return_value = "./conjur.pem"
        mock_fetch_conjur_token.return_value = "token"
        mock_fetch_conjur_variable.return_value = ["conjur_variable"]
        mock_merge_dictionaries.side_effect = [
            {'account': 'fakeaccount', 'appliance_url': 'https://conjur-fake', 'cert_file': './conjurfake.pem'},
            {'id': 'host/ansible/ansible-fake', 'api_key': 'fakekey'}
        ]

        terms = ['ansible/fake-secret']
        kwargs = {'as_file': True, 'conf_file': 'conf_file', 'validate_certs': False}
        filepaths = self.lookup.run(terms, **kwargs)
        self.assertRegex(filepaths[0], '/dev/shm/.*')

        with open(filepaths[0], "r") as file:
            content = file.read()
            self.assertEqual(content, "conjur_variable")

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_certificate_file')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_variable')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_token')
    def test_run_with_cert_content(self, mock_fetch_conjur_token, mock_fetch_conjur_variable, mock_get_certificate_file):
        mock_get_certificate_file.return_value = "./conjur.pem"
        mock_fetch_conjur_token.return_value = "token"
        mock_fetch_conjur_variable.return_value = ["conjur_variable"]

        variables = {'conjur_account': 'fakeaccount',
                     'conjur_appliance_url': 'https://conjur-fake',
                     'conjur_cert_content': '-----BEGIN CERTIFICATE-----\nFAKE CERT CONTENT\n-----END CERTIFICATE-----',
                     'conjur_authn_login': 'host/ansible/ansible-fake',
                     'conjur_authn_api_key': 'fakekey'}
        terms = ['ansible/fake-secret']

        output = self.lookup.run(terms, variables)
        self.assertEqual(output, ["conjur_variable"])

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_certificate_file')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_variable')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_token')
    def test_run_with_cert_content_and_file(self, mock_fetch_conjur_token, mock_fetch_conjur_variable, mock_get_certificate_file):
        mock_get_certificate_file.return_value = "./conjur.pem"
        mock_fetch_conjur_token.return_value = "token"
        mock_fetch_conjur_variable.return_value = ["conjur_variable"]

        variables = {'conjur_account': 'fakeaccount',
                     'conjur_appliance_url': 'https://conjur-fake',
                     'conjur_cert_content': '-----BEGIN CERTIFICATE-----\nFAKE CERT CONTENT\n-----END CERTIFICATE-----',
                     'conjur_cert_file': './conjurfake.pem',
                     'conjur_authn_login': 'host/ansible/ansible-fake',
                     'conjur_authn_api_key': 'fakekey'}
        terms = ['ansible/fake-secret']

        output = self.lookup.run(terms, variables)
        self.assertEqual(output, ["conjur_variable"])

    # Negative test cases

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_certificate_file')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._merge_dictionaries')
    def test_run_bad_config(self, mock_merge_dictionaries, mock_get_certificate_file):
        mock_get_certificate_file.return_value = "./conjur.pem"
        # Withhold 'account' field
        mock_merge_dictionaries.side_effect = [
            {'appliance_url': 'https://conjur-fake', 'cert_file': './conjurfake.pem'},
            {'id': 'host/ansible/ansible-fake', 'api_key': 'fakekey'}
        ]

        terms = ['ansible/fake-secret']
        kwargs = {'as_file': False, 'conf_file': 'conf_file', 'validate_certs': True}
        with self.assertRaises(AnsibleError) as context:
            self.lookup.run(terms, **kwargs)

        self.assertIn(
            "Configuration must define options `conjur_account` and `conjur_appliance_url`",
            context.exception.message,
        )

        # Withhold 'id' and 'api_key' fields
        mock_merge_dictionaries.side_effect = [
            {'account': 'fakeaccount', 'appliance_url': 'https://conjur-fake', 'cert_file': './conjurfake.pem'},
            {}
        ]

        with self.assertRaises(AnsibleError) as context:
            self.lookup.run(terms, **kwargs)

        self.assertIn(
            "Configuration must define options `conjur_authn_login` and `conjur_authn_api_key`",
            context.exception.message,
        )

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_certificate_file')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._merge_dictionaries')
    def test_run_bad_cert_path(self, mock_merge_dictionaries, mock_get_certificate_file):
        mock_get_certificate_file.return_value = "./conjur.pem"
        mock_merge_dictionaries.side_effect = [
            {'account': 'fakeaccount', 'appliance_url': 'https://conjur-fake', 'cert_file': './conjurfake.pem'},
            {'id': 'host/ansible/ansible-fake', 'api_key': 'fakekey'}
        ]

        terms = ['ansible/fake-secret']
        kwargs = {'as_file': False, 'conf_file': 'conf_file', 'validate_certs': True}
        with self.assertRaises(FileNotFoundError):
            self.lookup.run(terms, **kwargs)

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_variable')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_token')
    def test_run_with_invalid_cert_content(self, mock_fetch_conjur_token, mock_fetch_conjur_variable):
        mock_fetch_conjur_token.return_value = "token"
        mock_fetch_conjur_variable.return_value = ["conjur_variable"]

        variables = {'conjur_account': 'fakeaccount',
                     'conjur_appliance_url': 'https://conjur-fake',
                     'conjur_authn_login': 'host/ansible/ansible-fake',
                     'conjur_cert_content': 'dummy_cert',
                     'conjur_authn_api_key': 'fakekey'}
        terms = ['ansible/fake-secret']

        with self.assertRaises(AnsibleError) as context:
            self.lookup.run(terms, variables)

        self.assertIn(
            "Both certificate content and certificate file are invalid or missing. Please provide a valid certificate.",
            context.exception.message
        )

    def test_run_no_variable_path(self):
        kwargs = {'as_file': False, 'conf_file': 'conf_file', 'validate_certs': True}

        with self.assertRaises(AnsibleError) as context:
            self.lookup.run([], **kwargs)

        self.assertEqual(context.exception.message, "Invalid secret path: no secret path provided.")

        with self.assertRaises(AnsibleError) as context:
            self.lookup.run([''], **kwargs)

        self.assertEqual(context.exception.message, "Invalid secret path: empty secret path not accepted.")

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_variable')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_token')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_certificate_file')
    def test_run_missing_account(self, mock_fetch_conjur_token, mock_fetch_conjur_variable, mock_get_certificate_file):
        mock_fetch_conjur_token.return_value = "token"
        mock_fetch_conjur_variable.return_value = ["conjur_variable"]
        mock_get_certificate_file.return_value = "./conjur.pem"

        variables = {'conjur_cert_file': './conjurfake.pem',
                     'conjur_authn_login': 'host/ansible/ansible-fake',
                     'conjur_authn_api_key': 'fakekey'}
        terms = ['ansible/fake-secret']

        with self.assertRaises(AnsibleError) as context:
            self.lookup.run(terms, variables)

        self.assertIn(
            "Configuration must define options `conjur_account` and `conjur_appliance_url`",
            context.exception.message
        )

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_variable')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_token')
    def test_run_missing_certificate(self, mock_fetch_conjur_token, mock_fetch_conjur_variable):
        mock_fetch_conjur_token.return_value = "token"
        mock_fetch_conjur_variable.return_value = ["conjur_variable"]

        variables = {'conjur_account': 'fakeaccount',
                     'conjur_appliance_url': 'https://conjur-fake',
                     'conjur_authn_login': 'host/ansible/ansible-fake',
                     'conjur_authn_api_key': 'fakekey'}
        terms = ['ansible/fake-secret']

        with self.assertRaises(AnsibleError) as context:
            self.lookup.run(terms, variables)

        self.assertIn(
            "Both certificate content and certificate file are invalid or missing. Please provide a valid certificate.",
            context.exception.message
        )

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_variable')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_token')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_certificate_file')
    def test_run_missing_login(self, mock_fetch_conjur_token, mock_fetch_conjur_variable, mock_get_certificate_file):
        mock_fetch_conjur_token.return_value = "token"
        mock_fetch_conjur_variable.return_value = ["conjur_variable"]
        mock_get_certificate_file.return_value = "./conjur.pem"

        variables = {'conjur_account': 'fakeaccount',
                     'conjur_appliance_url': 'https://conjur-fake',
                     'conjur_cert_file': './conjurfake.pem'}
        terms = ['ansible/fake-secret']

        with self.assertRaises(AnsibleError) as context:
            self.lookup.run(terms, variables)

        self.assertIn(
            "Configuration must define options `conjur_authn_login` and `conjur_authn_api_key`",
            context.exception.message
        )

    def test_invalid_pem_certificate_no_start(self):
        cert_content = """MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQE7cWhPpOzzNUH5RzHoB89H
        -----END CERTIFICATE-----"""
        with self.assertRaises(AnsibleError) as context:
            _validate_pem_certificate(cert_content)

        self.assertIn("Invalid Certificate format.", str(context.exception))

    def test_invalid_pem_certificate_no_end(self):
        cert_content = """-----BEGIN CERTIFICATE-----
        MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQE7cWhPpOzzNUH5RzHoB89H
        """
        with self.assertRaises(AnsibleError) as context:
            _validate_pem_certificate(cert_content)

        self.assertIn("Invalid Certificate format.", str(context.exception))

    def test_certificate_parsing_error(self):
        cert_content = """-----BEGIN CERTIFICATE-----
        FakeCertificate
        -----END CERTIFICATE-----"""
        with self.assertRaises(AnsibleError) as context:
            _validate_pem_certificate(cert_content)

        self.assertIn("Invalid certificate content provided", str(context.exception))

    def test_invalid_certificate_format(self):
        cert_content = "not a PEM certificate"

        with self.assertRaises(AnsibleError) as context:
            _validate_pem_certificate(cert_content)

        self.assertIn("Invalid Certificate format.", str(context.exception))
