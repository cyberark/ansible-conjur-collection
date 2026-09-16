from __future__ import absolute_import, division, print_function
__metaclass__ = type

import hashlib
import hmac
import json
import os
import re
import socket
import ssl
import tempfile
import urllib.parse
from base64 import b64encode
from unittest import TestCase
from unittest.mock import MagicMock, patch, mock_open

from ansible.errors import AnsibleError
from ansible.module_utils.six.moves import urllib_error
from ansible.plugins.loader import lookup_loader

from ansible_collections.cyberark.conjur.plugins.lookup import conjur_variable as conjur_variable_module
from ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable import (
    _merge_dictionaries, _fetch_conjur_token, _fetch_conjur_variable,
    _validate_pem_certificate, _load_identity_from_file, _load_conf_from_file, _telemetry_header,
    _valid_aws_account_number, _sign, _get_signature_key, _get_aws_region,
    _get_metadata_token, _get_iam_role_metadata, _create_canonical_request,
    _create_conjur_iam_api_key, _get_iam_role_name, _fetch_conjur_iam_session_token,
    InvalidAwsAccountIdException, ConjurIAMAuthnException, _fetch_conjur_azure_token,
    _fetch_conjur_gcp_identity_token, _fetch_conjur_cert_token, _fetch_conjur_jwt_token,
    _read_jwt_token_file, _store_secret_in_file, _get_certificate_file, _get_valid_certificate,
    retry, _repeat_open_url, _validate_authn_cert_files,
)


class MockMergeDictionaries(MagicMock):
    RESPONSE = {'id': 'host/ansible/ansible-fake', 'api_key': 'fakekey'}


class MockFileload(MagicMock):
    RESPONSE = {}


class TestConjurLookup(TestCase):
    def setUp(self):
        self.lookup = lookup_loader.get("cyberark.conjur.conjur_variable")

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

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_fetch_conjur_token(self, mock_open_url, mock_telemetry_header):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = "response body"
        mock_open_url.return_value = mock_response
        mock_telemetry_header.return_value = 'fake_encoded_telemetry_value'
        result = _fetch_conjur_token("url", "account", "username", "api_key", True, "cert_file")
        mock_open_url.assert_called_with("url/authn/account/username/authenticate",
                                         data="api_key",
                                         method="POST",
                                         validate_certs=True,
                                         ca_path="cert_file",
                                         headers={'x-cybr-telemetry': 'fake_encoded_telemetry_value'})
        self.assertEqual("response body", result)

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._repeat_open_url')
    def test_fetch_conjur_variable(self, mock_repeat_open_url, mock_telemetry_header):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = "response body".encode("utf-8")
        mock_repeat_open_url.return_value = mock_response
        mock_telemetry_header.return_value = 'fake_encoded_telemetry_value'
        result = _fetch_conjur_variable("variable", b'{"protected":"fakeid"}', "url", "account", True, "cert_file")
        mock_repeat_open_url.assert_called_with(
            "url/secrets/account/variable/variable",
            headers={
                'Authorization': 'Token token="eyJwcm90ZWN0ZWQiOiJmYWtlaWQifQ=="',
                'x-cybr-telemetry': 'fake_encoded_telemetry_value'
            },
            method="GET",
            validate_certs=True,
            ca_path="cert_file",
            retry_interval=10
        )
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
    def test_retrieve_to_file(
            self, mock_merge_dictionaries, mock_fetch_conjur_token,
            mock_fetch_conjur_variable, mock_get_certificate_file):
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
        expected_dir = "/dev/shm" if os.access("/dev/shm", os.W_OK) else tempfile.gettempdir()
        self.assertRegex(filepaths[0], re.escape(expected_dir) + r'/.*')

        with open(filepaths[0], encoding='utf-8') as file:
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

    def test_run_telemetry_header(self):
        with patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.telemetry_header', new=None), \
             patch('os.path.isfile', return_value=True), \
             patch('builtins.open', mock_open(read_data='1.0.0')), \
             patch('os.path.abspath', return_value='/fake/path/to/collection'), \
             patch('os.path.dirname', return_value='/fake/path/to/plugin'):
            expected_version = '1.0.0'
            telemetry_val = f'in=Ansible Collections&it=cybr-secretsmanager&iv={expected_version}&vn=Ansible'
            expected_encoded = b64encode(telemetry_val.encode()).decode().rstrip("=")
            result = _telemetry_header()
            self.assertEqual(result, expected_encoded)

    def test_valid_aws_account_number_valid(self):
        self.assertTrue(_valid_aws_account_number("host/ansible/123456789012/test-resource"))

    def test_sign(self):
        key = b'secret'
        msg = 'message'
        expected = hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()
        self.assertEqual(_sign(key, msg), expected)

    def test_get_signature_key(self):
        key = 'testkey'
        date_stamp = '20250425'
        region_name = 'us-east-1'
        service_name = 'ec2'
        signing_key = _get_signature_key(key, date_stamp, region_name, service_name)
        self.assertIsInstance(signing_key, bytes)

    def test_get_aws_region(self):
        self.assertEqual(_get_aws_region(), "us-east-1")

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_get_metadata_token_success(self, mock_open_url):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'mock_token'
        mock_open_url.return_value = mock_response
        self.assertEqual(_get_metadata_token(), 'mock_token')

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_metadata_token')
    def test_get_iam_role_name_with_token(self, mock_get_metadata_token, mock_open_url):
        mock_get_metadata_token.return_value = 'fake-token'
        mock_response = MagicMock()
        mock_response.read.return_value = b'my-role-name'
        mock_open_url.return_value = mock_response

        result = _get_iam_role_name()

        self.assertEqual(result, 'my-role-name')
        mock_open_url.assert_called_once()
        args, kwargs = mock_open_url.call_args
        self.assertIn('headers', kwargs)
        self.assertEqual(kwargs['headers'], {'X-aws-ec2-metadata-token': 'fake-token'})

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_metadata_token')
    def test_get_iam_role_name_without_token(self, mock_get_metadata_token, mock_open_url):
        mock_get_metadata_token.return_value = None
        mock_response = MagicMock()
        mock_response.read.return_value = b'my-role-name'
        mock_open_url.return_value = mock_response
        result = _get_iam_role_name()
        self.assertEqual(result, 'my-role-name')
        args, kwargs = mock_open_url.call_args
        self.assertIn('headers', kwargs)
        self.assertEqual(kwargs['headers'], {})

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_get_iam_role_metadata_success(self, mock_open_url):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"AccessKeyId":"AKIA", "SecretAccessKey":"secret", "Token":"token"}'
        mock_open_url.return_value = mock_response
        result = _get_iam_role_metadata("role_name")
        self.assertEqual(result, ("AKIA", "secret", "token"))

    def test_create_canonical_request(self):
        payload_hash = hashlib.sha256(('').encode('utf-8')).hexdigest()
        result = _create_canonical_request(
            "20250425T123456Z",
            "token",
            "host;x-amz-content-sha256;x-amz-date;x-amz-security-token",
            payload_hash
        )
        self.assertIn("token", result)

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_iam_role_metadata')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_metadata_token')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_iam_role_name')
    def test_create_conjur_iam_api_key(self, mock_get_iam_role_name, mock_get_metadata_token, mock_get_iam_role_metadata):
        mock_get_iam_role_name.return_value = "test-role"
        mock_get_metadata_token.return_value = "token"
        mock_get_iam_role_metadata.return_value = ("AKIA", "secret", "token")
        result = _create_conjur_iam_api_key()
        self.assertIn('"authorization":', result)

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._valid_aws_account_number')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._create_conjur_iam_api_key')
    def test_fetch_conjur_iam_session_token_success(
            self, mock_create_conjur_iam_api_key, mock_telemetry_header,
            mock_valid_account, mock_open_url):
        mock_valid_account.return_value = True
        mock_telemetry_header.return_value = 'fake_encoded_telemetry_value'
        mock_create_conjur_iam_api_key.return_value = "fake_api_key"

        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b"session_token"
        mock_open_url.return_value = mock_response

        result = _fetch_conjur_iam_session_token(
            appliance_url='https://conjur-fake',
            account="fakeaccount",
            service_id="fake_service_id",
            host_id="fake_host_id",
            cert_file="path/fake-cert",
            validate_certs=True
        )
        self.assertEqual(result, b"session_token")

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header')
    @patch('urllib.parse.urlencode')
    def test_fetch_conjur_azure_token_success(self, mock_urlencode, mock_telemetry_header, mock_open_url):
        mock_urlencode.return_value = "api-version=2018-02-01&resource=https%3A%2F%2Fmanagement.azure.com%2F"
        mock_telemetry_header.return_value = "encoded_telemetry_data"

        mock_get_response = MagicMock()
        mock_get_response.getcode.return_value = 200
        mock_get_response.read.return_value = json.dumps({"access_token": "mocked_token"}).encode('utf-8')
        mock_open_url.return_value = mock_get_response

        mock_post_response = MagicMock()
        mock_post_response.getcode.return_value = 200
        mock_post_response.read.return_value = json.dumps({"status": "success"}).encode('utf-8')
        mock_open_url.return_value = mock_post_response

        appliance_url = "https://conjur-fake"
        account = "fakeaccount"
        service_id = "fake_service_id"
        host_id = "fake_host_id"
        cert_file = "/path/fake-cert.pem"
        validate_certs = True
        client_id = "fake_client_id"

        result = _fetch_conjur_azure_token(
            appliance_url, account, service_id,
            host_id, cert_file, validate_certs, client_id
        )

        self.assertEqual(result, mock_post_response.read())

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header')
    @patch('urllib.parse.urlencode')
    def test_fetch_conjur_azure_token_without_client_id(self, mock_urlencode, mock_telemetry_header, mock_open_url):
        mock_urlencode.return_value = "api-version=2018-02-01&resource=https%3A%2F%2Fmanagement.azure.com%2F"
        mock_telemetry_header.return_value = "encoded_telemetry_data"

        mock_get_response = MagicMock()
        mock_get_response.getcode.return_value = 200
        mock_get_response.read.return_value = json.dumps({"access_token": "mocked_token"}).encode('utf-8')
        mock_open_url.return_value = mock_get_response

        mock_post_response = MagicMock()
        mock_post_response.getcode.return_value = 200
        mock_post_response.read.return_value = json.dumps({"status": "success"}).encode('utf-8')
        mock_open_url.return_value = mock_post_response

        appliance_url = "https://conjur-fake"
        account = "fakeaccount"
        service_id = "fake_service_id"
        host_id = "fake_host_id"
        cert_file = "/path/fake-cert.pem"
        validate_certs = True

        result = _fetch_conjur_azure_token(
            appliance_url, account, service_id,
            host_id, cert_file, validate_certs
        )

        self.assertEqual(result, mock_post_response.read())

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_fetch_conjur_gcp_identity_token_success(self, mock_open_url, mock_telemetry_header):
        mock_telemetry_header.return_value = "encoded_telemetry_data"
        mock_get_response = MagicMock()
        mock_get_response.getcode.return_value = 200
        mock_get_response.read.return_value = b"gcp-jwt-token"
        mock_post_response = MagicMock()
        mock_post_response.getcode.return_value = 200
        mock_post_response.read.return_value = b"conjur-access-token"

        mock_open_url.side_effect = [mock_get_response, mock_post_response]

        appliance_url = "https://conjur-fake"
        account = "fakeaccount"
        host_id = "fake_host_id"
        cert_file = "/path/fake-cert.pem"
        validate_certs = True

        result = _fetch_conjur_gcp_identity_token(
            appliance_url, account, host_id,
            cert_file, validate_certs
        )
        self.assertEqual(result, b"conjur-access-token")

    # Negative test cases

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_certificate_file')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._merge_dictionaries')
    def test_run_bad_config(self, mock_merge_dictionaries, mock_get_certificate_file):
        mock_get_certificate_file.return_value = "./conjur.pem"
        # Withhold 'appliance_url' field
        mock_merge_dictionaries.side_effect = [
            {'cert_file': './conjurfake.pem'},
            {'id': 'host/ansible/ansible-fake', 'api_key': 'fakekey'}
        ]

        terms = ['ansible/fake-secret']
        kwargs = {'as_file': False, 'conf_file': 'conf_file', 'validate_certs': True}
        with self.assertRaises(AnsibleError) as context:
            self.lookup.run(terms, **kwargs)

        self.assertIn(
            "Configuration must define options `conjur_appliance_url`.",
            context.exception.message,
        )

        # Withhold 'id' field
        mock_merge_dictionaries.side_effect = [
            {'account': 'fakeaccount', 'appliance_url': 'https://conjur-fake', 'cert_file': './conjurfake.pem'},
            {}
        ]

        with self.assertRaises(AnsibleError) as context:
            self.lookup.run(terms, **kwargs)

        self.assertIn(
            "Configuration must define options `conjur_authn_login`.",
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
    def test_run_missing_certificate(self, mock_fetch_conjur_token, mock_fetch_conjur_variable):
        mock_fetch_conjur_token.return_value = b"token"
        mock_fetch_conjur_variable.return_value = ["conjur_variable"]

        variables = {'conjur_account': 'fakeaccount',
                     'conjur_appliance_url': 'https://conjur-fake',
                     'conjur_authn_login': 'host/ansible/ansible-fake',
                     'conjur_authn_api_key': 'fakekey'}
        terms = ['ansible/fake-secret']

        # No certificate provided – should succeed using the system trust store
        result = self.lookup.run(terms, variables)
        self.assertEqual(result, ["conjur_variable"])

        # Confirm that _fetch_conjur_token was called with ca_path=None,
        # meaning the system CA trust store is used.
        args, kwargs = mock_fetch_conjur_token.call_args
        self.assertIsNone(kwargs.get('cert_file') or (args[5] if len(args) > 5 else None))

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
            "Configuration must define options `conjur_authn_login`.",
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
        # Patch load_pem_x509_certificate to raise ValueError regardless of whether
        # the cryptography library is installed in the test environment.
        cert_content = """-----BEGIN CERTIFICATE-----
        FakeCertificate
        -----END CERTIFICATE-----"""
        # Both symbols may be absent when the cryptography package is not
        # installed in the test environment; create=True adds them temporarily.
        with patch(
            'ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.default_backend',
            return_value=None,
            create=True,
        ), patch(
            'ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.load_pem_x509_certificate',
            side_effect=ValueError('Could not deserialize key data'),
            create=True,
        ):
            with self.assertRaises(AnsibleError) as context:
                _validate_pem_certificate(cert_content)

        self.assertIn("Invalid certificate content provided", str(context.exception))

    def test_invalid_certificate_format(self):
        cert_content = "not a PEM certificate"

        with self.assertRaises(AnsibleError) as context:
            _validate_pem_certificate(cert_content)

        self.assertIn("Invalid Certificate format.", str(context.exception))

    def test_certificate_chain_multiple_blocks_accepted(self):
        cert_block = (
            "-----BEGIN CERTIFICATE-----\n"
            "FakeCertData\n"
            "-----END CERTIFICATE-----"
        )
        chain = cert_block + "\n" + cert_block
        with patch(
            'ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.default_backend',
            return_value=None,
            create=True,
        ), patch(
            'ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.load_pem_x509_certificate',
            return_value=None,
            create=True,
        ):
            result = _validate_pem_certificate(chain)
        self.assertIn("BEGIN CERTIFICATE", result)

    def test_valid_aws_account_number_invalid(self):
        self.assertFalse(_valid_aws_account_number("host/ansible/12345678901/test-resource"))

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_get_metadata_token_failure(self, mock_open_url):
        mock_open_url.side_effect = Exception("Failed")
        token = _get_metadata_token()
        self.assertIsNone(token)

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_get_iam_role_metadata_failure(self, mock_open_url):
        mock_open_url.side_effect = Exception("some error")
        with self.assertRaises(Exception):
            _get_iam_role_metadata("role_name")

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._valid_aws_account_number')
    def test_fetch_conjur_iam_session_token_invalid_account(self, mock_valid_account):
        mock_valid_account.return_value = False

        with self.assertRaises(InvalidAwsAccountIdException):
            _fetch_conjur_iam_session_token(
                appliance_url="https://conjur-fake",
                account="fakeaccount",
                service_id="fake_service_id",
                host_id="fake_host_id",
                cert_file="path/fake-cert",
                validate_certs=True
            )

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._valid_aws_account_number')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._create_conjur_iam_api_key')
    def test_fetch_conjur_iam_session_token_auth_failure(
            self, _mock_create_conjur_iam_api_key, mock_telemetry_header,
            mock_valid_account, mock_open_url):
        mock_valid_account.return_value = True
        mock_telemetry_header.return_value = 'fake_encoded_telemetry_value'

        mock_response = MagicMock()
        mock_response.getcode.return_value = 401
        mock_open_url.return_value = mock_response

        with self.assertRaises(ConjurIAMAuthnException):
            _fetch_conjur_iam_session_token(
                appliance_url="https://conjur-fake",
                account="fakeaccount",
                service_id="fake_service_id",
                host_id="fake_host_id",
                cert_file="path/fake-cert",
                validate_certs=True
            )

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._valid_aws_account_number')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._create_conjur_iam_api_key')
    def test_fetch_conjur_iam_session_token_http_error(
            self, _mock_create_conjur_iam_api_key, mock_telemetry_header,
            mock_valid_account, mock_open_url):
        mock_valid_account.return_value = True
        mock_telemetry_header.return_value = 'fake_encoded_telemetry_value'

        mock_response = MagicMock()
        mock_response.getcode.return_value = 500
        mock_open_url.return_value = mock_response

        with self.assertRaises(AnsibleError):
            _fetch_conjur_iam_session_token(
                appliance_url="https://conjur-fake",
                account="fakeaccount",
                service_id="fake_service_id",
                host_id="fake_host_id",
                cert_file="path/fake-cert",
                validate_certs=True
            )

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_fetch_conjur_azure_token_azure_failure(self, mock_open_url):
        mock_get_response = MagicMock()
        mock_get_response.getcode.return_value = 500
        mock_get_response.read.return_value = b"Internal Server Error"
        mock_open_url.return_value = mock_get_response

        appliance_url = "https://conjur-fake"
        account = "fakeaccount"
        service_id = "fake_service_id"
        host_id = "fake_host_id"
        cert_file = "/path/fakecert.pem"
        validate_certs = True
        client_id = "fake_client_id"

        with self.assertRaises(AnsibleError) as context:
            _fetch_conjur_azure_token(
                appliance_url, account, service_id,
                host_id, cert_file, validate_certs, client_id
            )

        self.assertIn("Error fetching identity token:", str(context.exception))

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_fetch_conjur_azure_token_conjur_unauthorized(self, mock_open_url):
        mock_get_response = MagicMock()
        mock_get_response.getcode.return_value = 200
        mock_get_response.read.return_value = json.dumps({"access_token": "mocked_token"}).encode('utf-8')
        mock_open_url.return_value = mock_get_response

        mock_post_response = MagicMock()
        mock_post_response.getcode.return_value = 401
        mock_post_response.read.return_value = b"Unauthorized"
        mock_open_url.return_value = mock_post_response

        appliance_url = "https://conjur-fake"
        account = "fakeaccount"
        service_id = "fake_service_id"
        host_id = "fake_host_id"
        cert_file = "/path/fakecert.pem"
        validate_certs = True
        client_id = "fake_client_id"

        with self.assertRaises(AnsibleError) as context:
            _fetch_conjur_azure_token(
                appliance_url, account, service_id,
                host_id, cert_file, validate_certs, client_id
            )

        self.assertIn("Error fetching identity token:", str(context.exception))

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_fetch_conjur_azure_token_invalid_json(self, mock_open_url):
        mock_get_response = MagicMock()
        mock_get_response.getcode.return_value = 200
        mock_get_response.read.return_value = b"invalid_json"
        mock_open_url.return_value = mock_get_response

        appliance_url = "https://conjur-fake"
        account = "fakeaccount"
        service_id = "fake_service_id"
        host_id = "fake_host_id"
        cert_file = "/path/fakecert.pem"
        validate_certs = True
        client_id = "fake_client_id"

        with self.assertRaises(AnsibleError) as context:
            _fetch_conjur_azure_token(
                appliance_url, account, service_id,
                host_id, cert_file, validate_certs, client_id
            )

        self.assertIn("Error fetching identity token:", str(context.exception))

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_fetch_conjur_gcp_identity_token_failure(self, mock_open_url, _mock_telemetry_header):
        mock_get_response = MagicMock()
        mock_get_response.getcode.return_value = 500
        mock_open_url.return_value = mock_get_response

        appliance_url = "https://conjur-fake"
        account = "fakeaccount"
        host_id = "fake_host_id"
        cert_file = "/path/fake-cert.pem"
        validate_certs = True

        with self.assertRaises(AnsibleError) as context:
            _fetch_conjur_gcp_identity_token(
                appliance_url, account, host_id,
                cert_file, validate_certs
            )
        self.assertIn("Error retrieving token from gcp", str(context.exception))

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_gcp_authenticate_endpoint_failure(self, mock_open_url, _mock_telemetry_header):
        mock_get_response = MagicMock()
        mock_get_response.getcode.return_value = 200
        mock_get_response.read.return_value = b"gcp-jwt-token"

        mock_post_response = MagicMock()
        mock_post_response.getcode.return_value = 403

        mock_open_url.side_effect = [mock_get_response, mock_post_response]

        appliance_url = "https://conjur-fake"
        account = "fakeaccount"
        host_id = "fake_host_id"
        cert_file = "/path/fake-cert.pem"
        validate_certs = True

        with self.assertRaises(AnsibleError) as context:
            _fetch_conjur_gcp_identity_token(
                appliance_url, account, host_id,
                cert_file, validate_certs
            )
        self.assertIn("Received status code 403", str(context.exception))

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_gcp_url_error(self, mock_open_url):
        mock_open_url.side_effect = urllib_error.URLError("Timeout")

        appliance_url = "https://conjur-fake"
        account = "fakeaccount"
        host_id = "fake_host_id"
        cert_file = "/path/fake-cert.pem"
        validate_certs = True

        with self.assertRaises(AnsibleError) as context:
            _fetch_conjur_gcp_identity_token(
                appliance_url, account, host_id,
                cert_file, validate_certs
            )
        self.assertIn("URL error occurred", str(context.exception))

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_gcp_generic_runtime_error(self, mock_open_url):
        mock_open_url.side_effect = RuntimeError("Unexpected failure")

        appliance_url = "https://conjur-fake"
        account = "fakeaccount"
        host_id = "fake_host_id"
        cert_file = "/path/fake-cert.pem"
        validate_certs = True

        with self.assertRaises(AnsibleError) as context:
            _fetch_conjur_gcp_identity_token(
                appliance_url, account, host_id,
                cert_file, validate_certs
            )
        self.assertIn("Unexpected failure", str(context.exception))

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_gcp_generic_exception(self, mock_open_url):
        mock_open_url.side_effect = Exception("Something went wrong")

        appliance_url = "https://conjur-fake"
        account = "fakeaccount"
        host_id = "fake_host_id"
        cert_file = "/path/fake-cert.pem"
        validate_certs = True

        with self.assertRaises(AnsibleError) as context:
            _fetch_conjur_gcp_identity_token(
                appliance_url, account, host_id,
                cert_file, validate_certs
            )
        self.assertIn("Something went wrong", str(context.exception))


class TestFetchConjurJwtToken(TestCase):
    """Unit tests for _fetch_conjur_jwt_token (authn-jwt)."""

    def _call(self, **overrides):
        defaults = {
            'appliance_url': 'https://conjur-fake',
            'account': 'fakeaccount',
            'service_id': 'jwt-service',
            'host_id': 'host/ansible/ansible-fake',
            'jwt_token': 'signed-jwt-payload',
            'cert_file': '/path/fake-ca.pem',
            'validate_certs': True,
        }
        defaults.update(overrides)
        return _fetch_conjur_jwt_token(**defaults)

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_fetch_conjur_jwt_token_success(self, mock_open_url, mock_telemetry_header):
        mock_telemetry_header.return_value = 'fake_telemetry'
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'conjur-session-token'
        mock_open_url.return_value = mock_response

        expected_host = urllib.parse.quote('host/ansible/ansible-fake', safe='')
        expected_url = (
            f'https://conjur-fake/authn-jwt/jwt-service/fakeaccount/'
            f'{expected_host}/authenticate'
        )

        result = self._call()

        self.assertEqual(result, b'conjur-session-token')
        mock_open_url.assert_called_once_with(
            expected_url,
            method='POST',
            data='jwt=signed-jwt-payload',
            headers={
                'x-cybr-telemetry': 'fake_telemetry',
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            validate_certs=True,
            ca_path='/path/fake-ca.pem',
            timeout=10,
        )

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_jwt_token_appliance_url_strips_trailing_slash(self, mock_open_url, mock_telemetry_header):
        mock_telemetry_header.return_value = 't'
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'ok'
        mock_open_url.return_value = mock_response

        self._call(appliance_url='https://conjur-fake/')

        url_used = mock_open_url.call_args[0][0]
        self.assertTrue(url_used.startswith('https://conjur-fake/authn-jwt/'))
        self.assertNotIn('conjur-fake//authn-jwt', url_used)

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_jwt_token_host_id_is_url_encoded(self, mock_open_url, mock_telemetry_header):
        mock_telemetry_header.return_value = 't'
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'ok'
        mock_open_url.return_value = mock_response

        self._call(host_id='host/vm-workloads/vm-01')

        url_used = mock_open_url.call_args[0][0]
        self.assertIn('host%2Fvm-workloads%2Fvm-01', url_used)

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_jwt_token_non200_raises_ansible_error(self, mock_open_url, mock_telemetry_header):
        mock_telemetry_header.return_value = 't'
        mock_response = MagicMock()
        mock_response.getcode.return_value = 401
        mock_open_url.return_value = mock_response

        with self.assertRaises(AnsibleError) as ctx:
            self._call()

        self.assertIn('HTTP 401', str(ctx.exception))

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_jwt_token_url_error(self, mock_open_url, mock_telemetry_header):
        mock_telemetry_header.return_value = 't'
        mock_open_url.side_effect = urllib_error.URLError('connection refused')

        with self.assertRaises(AnsibleError) as ctx:
            self._call()

        self.assertIn('URL error occurred', str(ctx.exception))
        self.assertIn('connection refused', str(ctx.exception))

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_jwt_token_http_error_raises_ansible_error(self, mock_open_url, mock_telemetry_header):
        """HTTPError from open_url should raise AnsibleError with HTTP status code."""
        mock_telemetry_header.return_value = 't'
        http_error = urllib_error.HTTPError(
            url='https://conjur/authn-jwt/svc/acc/host/authenticate',
            code=401,
            msg='Unauthorized',
            hdrs={},
            fp=None,
        )
        mock_open_url.side_effect = http_error

        with self.assertRaises(AnsibleError) as ctx:
            self._call()

        error_msg = str(ctx.exception)
        self.assertIn('401', error_msg)
        self.assertNotIn('CONJ', error_msg)

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_jwt_token_runtime_error(self, mock_open_url, mock_telemetry_header):
        mock_telemetry_header.return_value = 't'
        mock_open_url.side_effect = RuntimeError('tls handshake failed')

        with self.assertRaises(AnsibleError) as ctx:
            self._call()

        self.assertIn('tls handshake failed', str(ctx.exception))

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_jwt_token_generic_exception(self, mock_open_url, mock_telemetry_header):
        mock_telemetry_header.return_value = 't'
        mock_open_url.side_effect = ValueError('bad response')

        with self.assertRaises(AnsibleError) as ctx:
            self._call()

        self.assertIn('bad response', str(ctx.exception))

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_jwt_token_app_property_mode_url_excludes_host_id(self, mock_open_url, mock_telemetry_header):
        """When host_id is None (token-app-property mode) the URL must NOT contain a host segment."""
        mock_telemetry_header.return_value = 't'
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'conjur-token'
        mock_open_url.return_value = mock_response

        self._call(host_id=None)

        url_used = mock_open_url.call_args[0][0]
        # Must end with /{account}/authenticate, no extra path segment for host
        self.assertTrue(url_used.endswith('fakeaccount/authenticate'), url_used)
        self.assertNotIn('ansible', url_used)


class TestReadJwtTokenFile(TestCase):
    """Unit tests for _read_jwt_token_file."""

    FAKE_TOKEN_FILE = '/tmp/fake_jwt_token_test'

    @patch('os.stat')
    @patch('os.path.exists', return_value=True)
    def test_read_jwt_token_file_success(self, _mock_exists, mock_stat):
        """Returns stripped token content when file exists and has secure permissions."""
        mock_stat_result = MagicMock()
        mock_stat_result.st_mode = 0o100600
        mock_stat.return_value = mock_stat_result

        with patch('builtins.open', mock_open(read_data='my-signed-jwt-token\n')):
            result = _read_jwt_token_file(self.FAKE_TOKEN_FILE)

        self.assertEqual(result, 'my-signed-jwt-token')

    @patch('os.path.exists', return_value=False)
    def test_read_jwt_token_file_not_found_raises(self, _mock_exists):
        """Raises AnsibleError when the token file does not exist."""
        with self.assertRaises(AnsibleError) as ctx:
            _read_jwt_token_file(self.FAKE_TOKEN_FILE)

        self.assertIn('does not exist', str(ctx.exception))

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.display')
    @patch('os.stat')
    @patch('os.path.exists', return_value=True)
    def test_read_jwt_token_file_insecure_permissions_warns(self, _mock_exists, mock_stat, mock_display):
        """Issues a warning but still returns the token when permissions are too open."""
        mock_stat_result = MagicMock()
        mock_stat_result.st_mode = 0o100644  # group/other readable — insecure
        mock_stat.return_value = mock_stat_result

        with patch('builtins.open', mock_open(read_data='token-data')):
            result = _read_jwt_token_file(self.FAKE_TOKEN_FILE)

        self.assertEqual(result, 'token-data')
        mock_display.warning.assert_called_once()
        self.assertIn('insecure permissions', mock_display.warning.call_args[0][0])

    @patch('os.stat')
    @patch('os.path.exists', return_value=True)
    def test_read_jwt_token_file_os_error_raises(self, _mock_exists, mock_stat):
        """Raises AnsibleError wrapping the OSError when the file cannot be read."""
        mock_stat_result = MagicMock()
        mock_stat_result.st_mode = 0o100600
        mock_stat.return_value = mock_stat_result

        with patch('builtins.open', side_effect=OSError('permission denied')):
            with self.assertRaises(AnsibleError) as ctx:
                _read_jwt_token_file(self.FAKE_TOKEN_FILE)

        self.assertIn('Failed to read', str(ctx.exception))
        self.assertIn('permission denied', str(ctx.exception))


class TestLookupModuleJwt(TestCase):
    """run() integration tests for the authn-jwt authentication path."""

    _BASE_VARS = {
        'conjur_account': 'fakeaccount',
        'conjur_appliance_url': 'https://conjur-fake',
        'conjur_cert_file': './conjur.pem',
        'conjur_authn_login': 'host/ansible/ansible-jwt-host',
        'conjur_authn_type': 'jwt',
        'conjur_authn_service_id': 'jwt-service',
        'conjur_authn_jwt_token': 'signed-jwt-payload',
    }

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_certificate_file')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_variable')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_jwt_token')
    def test_run_jwt_url_mode(self, mock_fetch_jwt_token, mock_fetch_variable, mock_get_cert_file):
        """Default URL mode: host_id is included in the _fetch_conjur_jwt_token call."""
        mock_get_cert_file.return_value = './conjur.pem'
        mock_fetch_jwt_token.return_value = b'conjur-session-token'
        mock_fetch_variable.return_value = ['super_secret_value']

        lookup = lookup_loader.get('cyberark.conjur.conjur_variable')
        result = lookup.run(['ansible/fake-secret'], dict(self._BASE_VARS))

        self.assertEqual(result, ['super_secret_value'])
        mock_fetch_jwt_token.assert_called_once_with(
            appliance_url='https://conjur-fake',
            account='fakeaccount',
            service_id='jwt-service',
            host_id='host/ansible/ansible-jwt-host',
            jwt_token='signed-jwt-payload',
            validate_certs=True,
            cert_file='./conjur.pem',
        )

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_certificate_file')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_variable')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_jwt_token')
    def test_run_jwt_token_app_property_mode(self, mock_fetch_jwt_token, mock_fetch_variable, mock_get_cert_file):
        """token-app-property mode: no login required; host_id passed as None."""
        mock_get_cert_file.return_value = './conjur.pem'
        mock_fetch_jwt_token.return_value = b'conjur-session-token'
        mock_fetch_variable.return_value = ['super_secret_value']

        lookup = lookup_loader.get('cyberark.conjur.conjur_variable')
        variables = {
            'conjur_account': 'fakeaccount',
            'conjur_appliance_url': 'https://conjur-fake',
            'conjur_cert_file': './conjur.pem',
            # No conjur_authn_login — identity comes from JWT claim mapping
            'conjur_authn_type': 'jwt',
            'conjur_authn_service_id': 'jwt-service',
            'conjur_authn_jwt_token': 'signed-jwt-payload',
            'conjur_authn_jwt_mode': 'token-app-property',
        }
        result = lookup.run(['ansible/fake-secret'], variables)

        self.assertEqual(result, ['super_secret_value'])
        mock_fetch_jwt_token.assert_called_once_with(
            appliance_url='https://conjur-fake',
            account='fakeaccount',
            service_id='jwt-service',
            host_id=None,
            jwt_token='signed-jwt-payload',
            validate_certs=True,
            cert_file='./conjur.pem',
        )

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_certificate_file')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_variable')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_jwt_token')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._read_jwt_token_file')
    def test_run_jwt_with_token_file(
        self, mock_read_jwt_file, mock_fetch_jwt_token, mock_fetch_variable, mock_get_cert_file
    ):
        """When jwt_token_file is set and jwt_token is absent, _read_jwt_token_file is called."""
        mock_get_cert_file.return_value = './conjur.pem'
        mock_read_jwt_file.return_value = 'token-from-file'
        mock_fetch_jwt_token.return_value = b'conjur-session-token'
        mock_fetch_variable.return_value = ['super_secret_value']

        lookup = lookup_loader.get('cyberark.conjur.conjur_variable')
        variables = {
            'conjur_account': 'fakeaccount',
            'conjur_appliance_url': 'https://conjur-fake',
            'conjur_cert_file': './conjur.pem',
            'conjur_authn_login': 'host/ansible/ansible-jwt-host',
            'conjur_authn_type': 'jwt',
            'conjur_authn_service_id': 'jwt-service',
            'conjur_authn_jwt_token_file': '/run/secrets/jwt_token',
            # conjur_authn_jwt_token intentionally absent — plugin must read from file
        }
        result = lookup.run(['ansible/fake-secret'], variables)

        self.assertEqual(result, ['super_secret_value'])
        mock_read_jwt_file.assert_called_once_with('/run/secrets/jwt_token')
        mock_fetch_jwt_token.assert_called_once_with(
            appliance_url='https://conjur-fake',
            account='fakeaccount',
            service_id='jwt-service',
            host_id='host/ansible/ansible-jwt-host',
            jwt_token='token-from-file',
            validate_certs=True,
            cert_file='./conjur.pem',
        )

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_certificate_file')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_variable')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_jwt_token')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._read_jwt_token_file')
    def test_run_jwt_token_file_takes_precedence_over_token(
        self, mock_read_jwt_file, mock_fetch_jwt_token, mock_fetch_variable, mock_get_cert_file
    ):
        """When both are set, conjur_authn_jwt_token_file must win over conjur_authn_jwt_token
        (including when the latter is only populated via the CONJUR_AUTHN_JWT_TOKEN env fallback)."""
        mock_get_cert_file.return_value = './conjur.pem'
        mock_read_jwt_file.return_value = 'token-from-file'
        mock_fetch_jwt_token.return_value = b'conjur-session-token'
        mock_fetch_variable.return_value = ['super_secret_value']

        lookup = lookup_loader.get('cyberark.conjur.conjur_variable')
        variables = {
            'conjur_account': 'fakeaccount',
            'conjur_appliance_url': 'https://conjur-fake',
            'conjur_cert_file': './conjur.pem',
            'conjur_authn_login': 'host/ansible/ansible-jwt-host',
            'conjur_authn_type': 'jwt',
            'conjur_authn_service_id': 'jwt-service',
            'conjur_authn_jwt_token': 'ambient-token',
            'conjur_authn_jwt_token_file': '/run/secrets/jwt_token',
        }
        result = lookup.run(['ansible/fake-secret'], variables)

        self.assertEqual(result, ['super_secret_value'])
        mock_read_jwt_file.assert_called_once_with('/run/secrets/jwt_token')
        mock_fetch_jwt_token.assert_called_once_with(
            appliance_url='https://conjur-fake',
            account='fakeaccount',
            service_id='jwt-service',
            host_id='host/ansible/ansible-jwt-host',
            jwt_token='token-from-file',
            validate_certs=True,
            cert_file='./conjur.pem',
        )

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_certificate_file')
    def test_run_jwt_missing_service_id_raises(self, mock_get_cert_file):
        """AnsibleError is raised when conjur_authn_service_id is absent for authn-jwt."""
        mock_get_cert_file.return_value = './conjur.pem'

        lookup = lookup_loader.get('cyberark.conjur.conjur_variable')
        variables = {
            'conjur_account': 'fakeaccount',
            'conjur_appliance_url': 'https://conjur-fake',
            'conjur_cert_file': './conjur.pem',
            'conjur_authn_login': 'host/ansible/ansible-jwt-host',
            'conjur_authn_type': 'jwt',
            # conjur_authn_service_id intentionally absent
            'conjur_authn_jwt_token': 'signed-jwt-payload',
        }
        with self.assertRaises(AnsibleError):
            lookup.run(['ansible/fake-secret'], variables)


class TestFetchConjurCertToken(TestCase):
    """Unit tests for _fetch_conjur_cert_token (authn-x509 / authn-cert)."""

    # Fake file paths used across all _fetch_conjur_cert_token tests.
    _FAKE_CERT = '/tmp/fake_client.pem'
    _FAKE_KEY = '/tmp/fake_client.key'
    _FAKE_CA = '/tmp/fake_ca.pem'

    def setUp(self):
        # _validate_authn_cert_files now calls os.stat to check key-file permissions
        import os as _real_os
        _real_stat = _real_os.stat
        _fake_paths = {self._FAKE_CERT, self._FAKE_KEY, self._FAKE_CA}

        def _stat_side_effect(path, *args, **kwargs):
            if str(path) in _fake_paths:
                result = MagicMock()
                result.st_mode = 0o100600
                return result
            return _real_stat(path, *args, **kwargs)

        stat_patcher = patch('os.stat', side_effect=_stat_side_effect)
        stat_patcher.start()
        self.addCleanup(stat_patcher.stop)

    # ------------------------------------------------------------------ helpers
    def _call(self, **overrides):
        defaults = {
            'appliance_url': 'https://conjur-fake',
            'account': 'fakeaccount',
            'service_id': 'fake-service',
            'host_id': 'host/ansible/ansible-fake',
            'client_cert_file': '/tmp/fake_client.pem',
            'client_key_file': '/tmp/fake_client.key',
            'ca_cert_file': '/tmp/fake_ca.pem',
            'validate_certs': True,
        }
        defaults.update(overrides)
        return _fetch_conjur_cert_token(**defaults)

    # --------------------------------------------------------- success scenario
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    @patch('os.path.exists', return_value=True)
    def test_fetch_conjur_cert_token_success(self, _mock_exists, mock_open_url, mock_telemetry_header):
        mock_telemetry_header.return_value = 'fake_telemetry'
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'conjur-access-token'
        mock_open_url.return_value = mock_response

        fake_pem = "-----BEGIN CERTIFICATE-----\nFAKEBASE64DATA==\n-----END CERTIFICATE-----\n"

        with patch('builtins.open', mock_open(read_data=fake_pem)):
            result = self._call()

        expected_encoded_cert = urllib.parse.quote(fake_pem, safe='')

        self.assertEqual(result, b'conjur-access-token')
        mock_open_url.assert_called_once()
        call_args = mock_open_url.call_args
        # URL must use /authn-cert/ (not /authn-x509/)
        self.assertIn('/authn-cert/fake-service/fakeaccount/', call_args[0][0])
        self.assertNotIn('authn-x509', call_args[0][0])
        # Accept-Encoding: base64 must NOT be sent – _fetch_conjur_variable always
        # does b64encode(token) itself, so sending this header would cause double-encoding.
        self.assertNotIn('Accept-Encoding', call_args[1]['headers'])
        # Certificate is sent as X-SSL-Client-Certificate header (percent-encoded PEM).
        # client_cert / client_key are also passed so that a TLS-terminating proxy
        # (nginx with ssl_verify_client optional[_no_ca]) can extract the cert from
        # the mTLS handshake and forward it as the authoritative header value.
        self.assertEqual(call_args[1]['headers']['X-SSL-Client-Certificate'], expected_encoded_cert)
        self.assertEqual(call_args[1]['client_cert'], '/tmp/fake_client.pem')
        self.assertEqual(call_args[1]['client_key'], '/tmp/fake_client.key')
        self.assertEqual(call_args[1]['ca_path'], '/tmp/fake_ca.pem')
        self.assertTrue(call_args[1]['validate_certs'])

    # -------------------------------------------- URL path uses authn-cert (not authn-x509)
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    @patch('os.path.exists', return_value=True)
    def test_cert_token_url_uses_authn_cert_path(self, _mock_exists, mock_open_url, mock_telemetry_header):
        mock_telemetry_header.return_value = 'fake_telemetry'
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'token'
        mock_open_url.return_value = mock_response

        fake_pem = "-----BEGIN CERTIFICATE-----\nFAKEBASE64DATA==\n-----END CERTIFICATE-----\n"
        with patch('builtins.open', mock_open(read_data=fake_pem)):
            self._call()

        url_used = mock_open_url.call_args[0][0]
        self.assertTrue(url_used.startswith('https://conjur-fake/authn-cert/'))
        self.assertNotIn('authn-x509', url_used)

    # -------------------------------------------- Accept-Encoding: base64 must NOT be present
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    @patch('os.path.exists', return_value=True)
    def test_cert_token_no_accept_encoding_base64_header(self, _mock_exists, mock_open_url, mock_telemetry_header):
        """Accept-Encoding: base64 must NOT be sent.
        _fetch_conjur_variable always calls b64encode(token) on whatever bytes the
        authenticate endpoint returns.  If we also request base64 from Conjur,
        the token gets double-encoded and the subsequent secrets fetch returns 401."""
        mock_telemetry_header.return_value = 'fake_telemetry'
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'token'
        mock_open_url.return_value = mock_response

        fake_pem = "-----BEGIN CERTIFICATE-----\nFAKEBASE64DATA==\n-----END CERTIFICATE-----\n"
        with patch('builtins.open', mock_open(read_data=fake_pem)):
            self._call()

        headers = mock_open_url.call_args[1]['headers']
        self.assertNotIn('Accept-Encoding', headers)

    # -------------------------------------------- X-SSL-Client-Certificate header present (percent-encoded PEM)
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    @patch('os.path.exists', return_value=True)
    def test_cert_token_ssl_client_cert_header_present(self, _mock_exists, mock_open_url, mock_telemetry_header):
        mock_telemetry_header.return_value = 'fake_telemetry'
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'token'
        mock_open_url.return_value = mock_response

        fake_pem = "-----BEGIN CERTIFICATE-----\nFAKEBASE64DATA==\n-----END CERTIFICATE-----\n"
        expected_encoded = urllib.parse.quote(fake_pem, safe='')

        with patch('builtins.open', mock_open(read_data=fake_pem)):
            self._call()

        headers = mock_open_url.call_args[1]['headers']
        self.assertIn('X-SSL-Client-Certificate', headers)
        self.assertEqual(headers['X-SSL-Client-Certificate'], expected_encoded)
        # mTLS kwargs must be present so a TLS-terminating proxy can extract
        # the cert from the handshake and set the authoritative header value
        self.assertIn('client_cert', mock_open_url.call_args[1])
        self.assertIn('client_key', mock_open_url.call_args[1])

    # -------------------------------------------------- host_id URL-encoding (request mode)
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    @patch('os.path.exists', return_value=True)
    def test_cert_token_host_id_is_url_encoded(self, _mock_exists, mock_open_url, mock_telemetry_header):
        mock_telemetry_header.return_value = 'fake_telemetry'
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'token'
        mock_open_url.return_value = mock_response

        fake_pem = "-----BEGIN CERTIFICATE-----\nFAKEBASE64DATA==\n-----END CERTIFICATE-----\n"
        with patch('builtins.open', mock_open(read_data=fake_pem)):
            self._call(host_id='host/vm-workloads/vm-01')

        url_used = mock_open_url.call_args[0][0]
        # slashes inside host_id must be percent-encoded
        self.assertIn('host%2Fvm-workloads%2Fvm-01', url_used)

    # -------------------------------------------- SPIFFE mode: no host_id in URL
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    @patch('os.path.exists', return_value=True)
    def test_cert_token_spiffe_mode_no_host_id_in_url(self, _mock_exists, mock_open_url, mock_telemetry_header):
        mock_telemetry_header.return_value = 'fake_telemetry'
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'token'
        mock_open_url.return_value = mock_response

        # SPIFFE mode: host_id=None → URL must end with /authenticate (no workload segment)
        fake_pem = "-----BEGIN CERTIFICATE-----\nFAKEBASE64DATA==\n-----END CERTIFICATE-----\n"
        with patch('builtins.open', mock_open(read_data=fake_pem)):
            self._call(host_id=None)

        url_used = mock_open_url.call_args[0][0]
        self.assertEqual(
            url_used,
            'https://conjur-fake/authn-cert/fake-service/fakeaccount/authenticate'
        )

    # -------------------------------------------------- 401 Unauthorized
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    @patch('os.path.exists', return_value=True)
    def test_cert_token_401_raises_ansible_error(self, _mock_exists, mock_open_url, mock_telemetry_header):
        mock_telemetry_header.return_value = 'fake_telemetry'
        mock_open_url.side_effect = Exception('HTTP Error 401: Unauthorized')

        fake_pem = "-----BEGIN CERTIFICATE-----\nFAKEBASE64DATA==\n-----END CERTIFICATE-----\n"
        with patch('builtins.open', mock_open(read_data=fake_pem)):
            with self.assertRaises(AnsibleError) as ctx:
                self._call()

        self.assertIn('401', ctx.exception.message)

    # -------------------------------------------------- non-200/non-401 error
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    @patch('os.path.exists', return_value=True)
    def test_cert_token_non200_raises_ansible_error(self, _mock_exists, mock_open_url, mock_telemetry_header):
        mock_telemetry_header.return_value = 'fake_telemetry'
        mock_open_url.side_effect = Exception('HTTP Error 500: Internal Server Error')

        fake_pem = "-----BEGIN CERTIFICATE-----\nFAKEBASE64DATA==\n-----END CERTIFICATE-----\n"
        with patch('builtins.open', mock_open(read_data=fake_pem)):
            with self.assertRaises(AnsibleError) as ctx:
                self._call()

        self.assertIn('500', ctx.exception.message)

    # -------------------------------------------------- missing client cert
    @patch('os.path.exists', return_value=False)
    def test_cert_token_missing_client_cert_raises(self, _mock_exists):
        with self.assertRaises(AnsibleError) as ctx:
            self._call(client_cert_file='/nonexistent/client.pem')

        self.assertIn('client certificate file', ctx.exception.message.lower())

    # -------------------------------------------------- missing client key
    @patch('os.path.exists')
    def test_cert_token_missing_client_key_raises(self, mock_exists):
        # cert file exists, key file does not
        mock_exists.side_effect = lambda path: path == '/tmp/fake_client.pem'

        with self.assertRaises(AnsibleError) as ctx:
            self._call()

        self.assertIn('client key file', ctx.exception.message.lower())

    # -------------------------------------------------- network exception
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    @patch('os.path.exists', return_value=True)
    def test_cert_token_network_error_raises(self, _mock_exists, mock_open_url, mock_telemetry_header):
        mock_telemetry_header.return_value = 'fake_telemetry'
        mock_open_url.side_effect = Exception('Connection refused')

        fake_pem = "-----BEGIN CERTIFICATE-----\nFAKEBASE64DATA==\n-----END CERTIFICATE-----\n"
        with patch('builtins.open', mock_open(read_data=fake_pem)):
            with self.assertRaises(AnsibleError) as ctx:
                self._call()

        self.assertIn('Connection refused', ctx.exception.message)

    # -------------------------------------------------- run() integration with authn-cert (request mode)
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_certificate_file')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_variable')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_cert_token')
    def test_run_with_authn_cert(self, mock_fetch_cert_token, mock_fetch_variable, mock_get_certificate_file):
        mock_get_certificate_file.return_value = './conjur.pem'
        mock_fetch_cert_token.return_value = b'conjur-access-token'
        mock_fetch_variable.return_value = ['super_secret_value']

        lookup = lookup_loader.get('cyberark.conjur.conjur_variable')
        variables = {
            'conjur_account': 'fakeaccount',
            'conjur_appliance_url': 'https://conjur-fake',
            'conjur_cert_file': './conjur.pem',
            'conjur_authn_login': 'host/ansible/ansible-fake',
            'conjur_authn_type': 'authn-cert',
            'conjur_authn_service_id': 'x509-service',
            'conjur_client_cert_file': '/tmp/client.pem',
            'conjur_client_key_file': '/tmp/client.key',
        }
        result = lookup.run(['ansible/fake-secret'], variables)
        self.assertEqual(result, ['super_secret_value'])
        mock_fetch_cert_token.assert_called_once_with(
            appliance_url='https://conjur-fake',
            account='fakeaccount',
            service_id='x509-service',
            host_id='host/ansible/ansible-fake',
            client_cert_file='/tmp/client.pem',
            client_key_file='/tmp/client.key',
            ca_cert_file='./conjur.pem',
            validate_certs=True,
        )

    # ------------------------------------------ run() with authn-cert SPIFFE mode
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_certificate_file')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_variable')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_cert_token')
    def test_run_with_authn_cert_spiffe_mode(self, mock_fetch_cert_token, mock_fetch_variable, mock_get_certificate_file):
        mock_get_certificate_file.return_value = './conjur.pem'
        mock_fetch_cert_token.return_value = b'conjur-access-token'
        mock_fetch_variable.return_value = ['super_secret_value']

        lookup = lookup_loader.get('cyberark.conjur.conjur_variable')
        variables = {
            'conjur_account': 'fakeaccount',
            'conjur_appliance_url': 'https://conjur-fake',
            'conjur_cert_file': './conjur.pem',
            # No conjur_authn_login — SPIFFE mode derives identity from certificate
            'conjur_authn_type': 'authn-cert',
            'conjur_authn_service_id': 'x509-service',
            'conjur_authn_cert_mode': 'spiffe',
            'conjur_client_cert_file': '/tmp/client.pem',
            'conjur_client_key_file': '/tmp/client.key',
        }
        result = lookup.run(['ansible/fake-secret'], variables)
        self.assertEqual(result, ['super_secret_value'])
        # In SPIFFE mode host_id must be None so it is absent from the URL
        mock_fetch_cert_token.assert_called_once_with(
            appliance_url='https://conjur-fake',
            account='fakeaccount',
            service_id='x509-service',
            host_id=None,
            client_cert_file='/tmp/client.pem',
            client_key_file='/tmp/client.key',
            ca_cert_file='./conjur.pem',
            validate_certs=True,
        )

    # ------------------------------------------ run(): missing service_id for authn-cert
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_certificate_file')
    def test_run_authn_cert_missing_service_id_raises(self, mock_get_cert_file):
        mock_get_cert_file.return_value = './conjur.pem'

        lookup = lookup_loader.get('cyberark.conjur.conjur_variable')
        variables = {
            'conjur_account': 'fakeaccount',
            'conjur_appliance_url': 'https://conjur-fake',
            'conjur_cert_file': './conjur.pem',
            'conjur_authn_login': 'host/ansible/ansible-fake',
            'conjur_authn_type': 'authn-cert',
            # conjur_authn_service_id intentionally omitted
            'conjur_client_cert_file': '/tmp/client.pem',
            'conjur_client_key_file': '/tmp/client.key',
        }
        with self.assertRaises(AnsibleError):
            lookup.run(['ansible/fake-secret'], variables)


class TestStoreSecretInFile(TestCase):
    def test_returns_file_path_containing_secret(self):
        with patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.atexit.register'):
            result = _store_secret_in_file(['mysecret'])

        path = result[0]
        try:
            self.assertTrue(os.path.exists(path))
            with open(path, encoding='utf-8') as f:
                self.assertEqual(f.read(), 'mysecret')
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_file_has_user_only_permissions(self):
        with patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.atexit.register'):
            result = _store_secret_in_file(['mysecret'])

        path = result[0]
        try:
            mode = oct(os.stat(path).st_mode)
            self.assertTrue(mode.endswith('600'), f"expected mode 600, got {mode}")
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_atexit_callback_deletes_file(self):
        registered_callbacks = []

        def capture_register(fn, *args, **kwargs):
            registered_callbacks.append((fn, args, kwargs))

        with patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.atexit.register', side_effect=capture_register):
            result = _store_secret_in_file(['mysecret'])

        path = result[0]
        try:
            self.assertEqual(len(registered_callbacks), 1)
            fn, args, kwargs = registered_callbacks[0]
            self.assertTrue(os.path.exists(path))
            fn(*args, **kwargs)
            self.assertFalse(os.path.exists(path))
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_atexit_callback_is_idempotent_when_file_already_deleted(self):
        registered_callbacks = []

        def capture_register(fn, *args, **kwargs):
            registered_callbacks.append((fn, args, kwargs))

        with patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.atexit.register', side_effect=capture_register):
            result = _store_secret_in_file(['mysecret'])

        path = result[0]
        os.unlink(path)

        fn, args, kwargs = registered_callbacks[0]
        # should not raise even though file is already gone
        fn(*args, **kwargs)
        self.assertFalse(os.path.exists(path))


class TestRetryDecorator(TestCase):
    """Unit tests for the retry() decorator."""

    def test_retry_succeeds_without_retry(self):
        target = MagicMock(return_value="ok")
        wrapped = retry(retries=3, retry_interval=0)(target)

        self.assertEqual(wrapped(), "ok")
        self.assertEqual(target.call_count, 1)

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.sleep')
    def test_retry_recovers_after_socket_timeout(self, mock_sleep):
        target = MagicMock(side_effect=[socket.timeout("timed out"), socket.timeout("timed out"), "ok"])
        wrapped = retry(retries=5, retry_interval=7)(target)

        result = wrapped()

        self.assertEqual(result, "ok")
        self.assertEqual(target.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_called_with(7)

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.sleep')
    def test_retry_recovers_after_url_error(self, mock_sleep):
        target = MagicMock(side_effect=[urllib_error.URLError("boom"), "ok"])
        wrapped = retry(retries=5, retry_interval=0)(target)

        result = wrapped()

        self.assertEqual(result, "ok")
        self.assertEqual(target.call_count, 2)
        mock_sleep.assert_called_once_with(0)

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.sleep')
    def test_retry_raises_after_exhausting_attempts(self, mock_sleep):
        target = MagicMock(side_effect=socket.timeout("still timing out"))
        wrapped = retry(retries=3, retry_interval=0)(target)

        with self.assertRaises(socket.timeout):
            wrapped()

        self.assertEqual(target.call_count, 3)
        # Only retried twice - no sleep after the final, non-retried failure.
        self.assertEqual(mock_sleep.call_count, 2)

    def test_retry_does_not_retry_non_network_errors(self):
        target = MagicMock(side_effect=ValueError("not retryable"))
        wrapped = retry(retries=5, retry_interval=0)(target)

        with self.assertRaises(ValueError):
            wrapped()

        self.assertEqual(target.call_count, 1)


class TestRepeatOpenUrl(TestCase):
    """Unit tests for _repeat_open_url()."""

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_repeat_open_url_success_no_retry(self, mock_open_url):
        mock_response = MagicMock()
        mock_open_url.return_value = mock_response

        result = _repeat_open_url("https://conjur-fake/x", retry_interval=0)

        self.assertIs(result, mock_response)
        self.assertEqual(mock_open_url.call_count, 1)

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.sleep')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_repeat_open_url_retries_on_socket_timeout_then_succeeds(self, mock_open_url, mock_sleep):
        mock_response = MagicMock()
        mock_open_url.side_effect = [socket.timeout("timed out"), mock_response]

        result = _repeat_open_url("https://conjur-fake/x", retry_interval=5)

        self.assertIs(result, mock_response)
        self.assertEqual(mock_open_url.call_count, 2)
        mock_sleep.assert_called_once_with(5)

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.sleep')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_repeat_open_url_retries_on_url_error_then_succeeds(self, mock_open_url, mock_sleep):
        mock_response = MagicMock()
        mock_open_url.side_effect = [urllib_error.URLError("conn refused"), mock_response]

        result = _repeat_open_url("https://conjur-fake/x", retry_interval=0)

        self.assertIs(result, mock_response)
        self.assertEqual(mock_open_url.call_count, 2)

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.sleep')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_repeat_open_url_reraises_after_exhausting_retries(self, mock_open_url, mock_sleep):
        mock_open_url.side_effect = socket.timeout("still timing out")

        with self.assertRaises(socket.timeout):
            _repeat_open_url("https://conjur-fake/x", retry_interval=0)

        # _repeat_open_url hard-codes retries=5
        self.assertEqual(mock_open_url.call_count, 5)
        self.assertEqual(mock_sleep.call_count, 4)

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_repeat_open_url_does_not_retry_other_exceptions(self, mock_open_url):
        mock_open_url.side_effect = ValueError("boom")

        with self.assertRaises(ValueError):
            _repeat_open_url("https://conjur-fake/x", retry_interval=0)

        self.assertEqual(mock_open_url.call_count, 1)


class TestValidatePemCertificateAdditionalBranches(TestCase):
    """Covers CRLF-only normalization and the ssl.SSLError / generic-exception handlers
    of _validate_pem_certificate(), which aren't exercised by the pre-existing tests."""

    @staticmethod
    def _patch_loader(**kwargs):
        loader_patch = patch(
            'ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.load_pem_x509_certificate',
            create=True, **kwargs
        )
        backend_patch = patch(
            'ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.default_backend',
            return_value=None, create=True,
        )
        return loader_patch, backend_patch

    def test_bare_cr_line_endings_are_normalized(self):
        cert_block = (
            "-----BEGIN CERTIFICATE-----\r"
            "FakeCertData\r"
            "-----END CERTIFICATE-----"
        )
        loader_patch, backend_patch = self._patch_loader(return_value=None)
        with loader_patch, backend_patch:
            result = _validate_pem_certificate(cert_block)

        self.assertNotIn('\r', result)
        self.assertIn('-----BEGIN CERTIFICATE-----', result)

    def test_crlf_line_endings_are_normalized(self):
        cert_block = (
            "-----BEGIN CERTIFICATE-----\r\n"
            "FakeCertData\r\n"
            "-----END CERTIFICATE-----"
        )
        loader_patch, backend_patch = self._patch_loader(return_value=None)
        with loader_patch, backend_patch:
            result = _validate_pem_certificate(cert_block)

        self.assertNotIn('\r', result)
        self.assertIn('-----BEGIN CERTIFICATE-----', result)

    def test_ssl_error_is_wrapped(self):
        cert_block = (
            "-----BEGIN CERTIFICATE-----\n"
            "FakeCertData\n"
            "-----END CERTIFICATE-----"
        )
        loader_patch, backend_patch = self._patch_loader(side_effect=ssl.SSLError("bad handshake data"))
        with loader_patch, backend_patch:
            with self.assertRaises(AnsibleError) as ctx:
                _validate_pem_certificate(cert_block)

        self.assertIn("SSL error while validating the certificate", str(ctx.exception))

    def test_generic_exception_is_wrapped(self):
        cert_block = (
            "-----BEGIN CERTIFICATE-----\n"
            "FakeCertData\n"
            "-----END CERTIFICATE-----"
        )
        loader_patch, backend_patch = self._patch_loader(side_effect=RuntimeError("unexpected"))
        with loader_patch, backend_patch:
            with self.assertRaises(AnsibleError) as ctx:
                _validate_pem_certificate(cert_block)

        self.assertIn("An error occurred while validating the certificate", str(ctx.exception))


class TestGetValidCertificate(TestCase):
    """Unit tests for _get_valid_certificate()."""

    @staticmethod
    def _patch_loader(**kwargs):
        loader_patch = patch(
            'ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.load_pem_x509_certificate',
            create=True, **kwargs
        )
        backend_patch = patch(
            'ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.default_backend',
            return_value=None, create=True,
        )
        return loader_patch, backend_patch

    def test_returns_none_when_neither_provided(self):
        self.assertIsNone(_get_valid_certificate(None, None))

    def test_returns_validated_content_when_content_is_valid(self):
        cert_content = "-----BEGIN CERTIFICATE-----\nFakeCertData\n-----END CERTIFICATE-----"
        loader_patch, backend_patch = self._patch_loader(return_value=None)
        with loader_patch, backend_patch:
            result = _get_valid_certificate(cert_content, None)

        self.assertIn("BEGIN CERTIFICATE", result)

    def test_falls_back_to_cert_file_when_content_invalid(self):
        cert_file_content = "-----BEGIN CERTIFICATE-----\nFileCertData\n-----END CERTIFICATE-----"
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as fh:
            fh.write(cert_file_content)
            cert_file_path = fh.name

        try:
            loader_patch, backend_patch = self._patch_loader(return_value=None)
            with loader_patch, backend_patch:
                result = _get_valid_certificate("not a real cert", cert_file_path)

            self.assertIn("FileCertData", result)
        finally:
            os.unlink(cert_file_path)

    def test_raises_when_cert_file_does_not_exist(self):
        with self.assertRaises(AnsibleError) as ctx:
            _get_valid_certificate(None, "/nonexistent/path/to/cert.pem")

        self.assertIn("does not exist", str(ctx.exception))

    def test_raises_when_both_content_and_file_invalid(self):
        with self.assertRaises(AnsibleError) as ctx:
            _get_valid_certificate("not a real cert", None)

        self.assertIn(
            "Both certificate content and certificate file are invalid or missing",
            str(ctx.exception),
        )

    def test_raises_when_cert_file_read_fails(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as fh:
            fh.write("-----BEGIN CERTIFICATE-----\nX\n-----END CERTIFICATE-----")
            cert_file_path = fh.name

        try:
            with patch('builtins.open', side_effect=OSError("permission denied")):
                with self.assertRaises(AnsibleError) as ctx:
                    _get_valid_certificate(None, cert_file_path)

            self.assertIn("Failed to load or validate certificate file", str(ctx.exception))
        finally:
            os.unlink(cert_file_path)


class TestGetCertificateFile(TestCase):
    """Unit tests for _get_certificate_file()."""

    @staticmethod
    def _patch_loader(**kwargs):
        loader_patch = patch(
            'ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.load_pem_x509_certificate',
            create=True, **kwargs
        )
        backend_patch = patch(
            'ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.default_backend',
            return_value=None, create=True,
        )
        return loader_patch, backend_patch

    def setUp(self):
        conjur_variable_module.temp_cert_file = None

    def tearDown(self):
        temp_file = conjur_variable_module.temp_cert_file
        if temp_file is not None and os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
        conjur_variable_module.temp_cert_file = None

    def test_returns_none_cert_file_when_no_cert_provided(self):
        self.assertIsNone(_get_certificate_file(None, None))

    def test_builds_bundle_with_real_system_ca_and_custom_cert(self):
        cert_content = "-----BEGIN CERTIFICATE-----\nCustomCertData\n-----END CERTIFICATE-----"
        system_ca_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
        system_ca_file.write("-----BEGIN CERTIFICATE-----\nSystemCaData\n-----END CERTIFICATE-----\n")
        system_ca_file.close()

        try:
            fake_paths = MagicMock(cafile=system_ca_file.name)
            loader_patch, backend_patch = self._patch_loader(return_value=None)
            with loader_patch, backend_patch, patch(
                'ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.ssl.get_default_verify_paths',
                return_value=fake_paths,
            ):
                result_path = _get_certificate_file(cert_content, None)

            self.assertIsNotNone(result_path)
            with open(result_path, encoding='utf-8') as f:
                bundle_contents = f.read()
            self.assertIn("SystemCaData", bundle_contents)
            self.assertIn("CustomCertData", bundle_contents)
        finally:
            os.unlink(system_ca_file.name)

    def test_warns_and_uses_only_custom_cert_when_no_system_bundle(self):
        cert_content = "-----BEGIN CERTIFICATE-----\nCustomCertData\n-----END CERTIFICATE-----"
        fake_paths = MagicMock(cafile=None)

        loader_patch, backend_patch = self._patch_loader(return_value=None)
        with loader_patch, backend_patch, patch(
            'ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.ssl.get_default_verify_paths',
            return_value=fake_paths,
        ), patch(
            'ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.display'
        ) as mock_display:
            result_path = _get_certificate_file(cert_content, None)

        with open(result_path, encoding='utf-8') as f:
            bundle_contents = f.read()
        self.assertIn("CustomCertData", bundle_contents)
        mock_display.warning.assert_called_once()
        self.assertIn("System CA bundle not found", mock_display.warning.call_args[0][0])

    def test_falls_back_to_cert_file_content_and_builds_bundle(self):
        cert_file_content = "-----BEGIN CERTIFICATE-----\nFileCertData\n-----END CERTIFICATE-----"
        cert_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
        cert_file.write(cert_file_content)
        cert_file.close()
        fake_paths = MagicMock(cafile=None)

        try:
            loader_patch, backend_patch = self._patch_loader(return_value=None)
            with loader_patch, backend_patch, patch(
                'ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.ssl.get_default_verify_paths',
                return_value=fake_paths,
            ):
                result_path = _get_certificate_file("not a real cert", cert_file.name)

            self.assertNotEqual(result_path, cert_file.name)
            with open(result_path, encoding='utf-8') as f:
                self.assertIn("FileCertData", f.read())
        finally:
            os.unlink(cert_file.name)

    def test_both_content_and_file_invalid_raises(self):
        with self.assertRaises(AnsibleError) as ctx:
            _get_certificate_file("not a real cert", None)

        self.assertIn(
            "Both certificate content and certificate file are invalid or missing",
            str(ctx.exception),
        )

    def test_raises_when_bundle_creation_fails(self):
        cert_content = "-----BEGIN CERTIFICATE-----\nCustomCertData\n-----END CERTIFICATE-----"
        loader_patch, backend_patch = self._patch_loader(return_value=None)
        with loader_patch, backend_patch, patch(
            'ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.NamedTemporaryFile',
            side_effect=OSError("disk full"),
        ):
            with self.assertRaises(AnsibleError) as ctx:
                _get_certificate_file(cert_content, None)

        self.assertIn("Failed to create temporary CA bundle", str(ctx.exception))


class TestLoadFromFileRealPaths(TestCase):
    """Unit tests exercising the real file-reading branches of _load_conf_from_file()
    and _load_identity_from_file() (CONJ-101), which other tests only reach via the
    'file does not exist' early-return branch."""

    def test_load_conf_from_file_reads_real_yaml(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as conf_file:
            conf_file.write("account: fakeaccount\nappliance_url: https://conjur-fake\n")
            conf_path = conf_file.name
        try:
            result = _load_conf_from_file(conf_path)
            self.assertEqual(result, {'account': 'fakeaccount', 'appliance_url': 'https://conjur-fake'})
        finally:
            os.unlink(conf_path)

    def test_load_identity_from_file_reads_real_netrc_entry(self):
        appliance_url = 'https://conjur-fake'
        with tempfile.NamedTemporaryFile(mode='w', suffix='.identity', delete=False) as identity_file:
            identity_file.write(
                f"machine {appliance_url}/authn\n"
                "  login host/ansible/ansible-fake\n"
                "  password fakekey\n"
            )
            identity_path = identity_file.name
        try:
            result = _load_identity_from_file(identity_path, appliance_url)
            self.assertEqual(result, {'id': 'host/ansible/ansible-fake', 'api_key': 'fakekey'})
        finally:
            os.unlink(identity_path)

    def test_load_identity_from_file_missing_entry_raises(self):
        appliance_url = 'https://conjur-fake'
        with tempfile.NamedTemporaryFile(mode='w', suffix='.identity', delete=False) as identity_file:
            identity_file.write(
                "machine https://some-other-host/authn\n"
                "  login host/ansible/other\n"
                "  password otherkey\n"
            )
            identity_path = identity_file.name
        try:
            with self.assertRaises(AnsibleError) as context:
                _load_identity_from_file(identity_path, appliance_url)
            self.assertIn("does not contain an entry for", str(context.exception))
        finally:
            os.unlink(identity_path)


class TestAwsMetadataBranches(TestCase):
    """Unit tests for AWS IMDS helper error branches not exercised elsewhere (CONJ-101)."""

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_get_metadata_token_non_200_returns_none(self, mock_open_url):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 400
        mock_response.read.return_value = b''
        mock_open_url.return_value = mock_response

        self.assertIsNone(_get_metadata_token())

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_get_iam_role_metadata_404_raises(self, mock_open_url):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 404
        mock_open_url.return_value = mock_response

        with self.assertRaises(AnsibleError) as context:
            _get_iam_role_metadata("role_name")
        self.assertIn("Error retrieving IAM role metadata", str(context.exception))

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_get_iam_role_metadata_non_200_raises(self, mock_open_url):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 500
        mock_open_url.return_value = mock_response

        with self.assertRaises(AnsibleError) as context:
            _get_iam_role_metadata("role_name")
        self.assertIn("Error retrieving IAM role metadata", str(context.exception))

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_iam_role_metadata')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_metadata_token')
    def test_create_conjur_iam_api_key_no_access_key_raises(self, mock_get_metadata_token, mock_get_iam_role_metadata):
        mock_get_metadata_token.return_value = 'fake-token'
        mock_get_iam_role_metadata.return_value = (None, None, None)

        with self.assertRaises(AnsibleError) as context:
            _create_conjur_iam_api_key(iam_role_name='fake-role')
        self.assertIn("No access key is available", str(context.exception))

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_metadata_token')
    def test_create_conjur_iam_api_key_uses_provided_role_name(self, mock_get_metadata_token):
        mock_get_metadata_token.return_value = 'fake-token'

        result = _create_conjur_iam_api_key(
            iam_role_name='fake-role', access_key='AKIA...', secret_key='secret', token='session-token'
        )
        self.assertIn('"authorization"', result)


class TestFetchConjurVariableErrorCodes(TestCase):
    """Unit tests for _fetch_conjur_variable() non-200 response branches (CONJ-102)."""

    def _mock_response(self, code):
        response = MagicMock()
        response.getcode.return_value = code
        return response

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header', return_value='telemetry')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._repeat_open_url')
    def test_401_raises_ansible_error(self, mock_repeat_open_url, _mock_telemetry_header):
        mock_repeat_open_url.return_value = self._mock_response(401)

        with self.assertRaises(AnsibleError) as context:
            _fetch_conjur_variable('fake-var', b'token', 'https://conjur-fake', 'fakeaccount', True, None)
        self.assertIn("invalid authorization credentials", str(context.exception))

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header', return_value='telemetry')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._repeat_open_url')
    def test_403_raises_ansible_error(self, mock_repeat_open_url, _mock_telemetry_header):
        mock_repeat_open_url.return_value = self._mock_response(403)

        with self.assertRaises(AnsibleError) as context:
            _fetch_conjur_variable('fake-var', b'token', 'https://conjur-fake', 'fakeaccount', True, None)
        self.assertIn("does not have authorization to retrieve", str(context.exception))

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header', return_value='telemetry')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._repeat_open_url')
    def test_404_raises_ansible_error(self, mock_repeat_open_url, _mock_telemetry_header):
        mock_repeat_open_url.return_value = self._mock_response(404)

        with self.assertRaises(AnsibleError) as context:
            _fetch_conjur_variable('fake-var', b'token', 'https://conjur-fake', 'fakeaccount', True, None)
        self.assertIn("does not exist", str(context.exception))

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header', return_value='telemetry')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._repeat_open_url')
    def test_unexpected_code_returns_empty_dict(self, mock_repeat_open_url, _mock_telemetry_header):
        mock_repeat_open_url.return_value = self._mock_response(500)

        result = _fetch_conjur_variable('fake-var', b'token', 'https://conjur-fake', 'fakeaccount', True, None)
        self.assertEqual(result, {})


class TestFetchConjurTokenErrorCodes(TestCase):
    """Unit test for _fetch_conjur_token() non-200 response branch (CONJ-102)."""

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._telemetry_header', return_value='telemetry')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.open_url')
    def test_non_200_raises_ansible_error(self, mock_open_url, _mock_telemetry_header):
        response = MagicMock()
        response.getcode.return_value = 401
        mock_open_url.return_value = response

        with self.assertRaises(AnsibleError) as context:
            _fetch_conjur_token('https://conjur-fake', 'fakeaccount', 'host/fake', 'fakekey', True, None)
        self.assertIn("Failed to authenticate as 'host/fake'", str(context.exception))


class TestLookupModuleAwsAzureGcp(TestCase):
    """End-to-end LookupModule.run() dispatch tests for aws/azure/gcp authenticators (CONJ-102)."""

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_certificate_file')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_variable')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_iam_session_token')
    def test_run_with_aws_authenticator(self, mock_fetch_iam_token, mock_fetch_variable, mock_get_cert_file):
        mock_get_cert_file.return_value = './conjur.pem'
        mock_fetch_iam_token.return_value = b'conjur-access-token'
        mock_fetch_variable.return_value = ['super_secret_value']

        lookup = lookup_loader.get('cyberark.conjur.conjur_variable')
        variables = {
            'conjur_account': 'fakeaccount',
            'conjur_appliance_url': 'https://conjur-fake',
            'conjur_cert_file': './conjur.pem',
            'conjur_authn_login': 'host/aws/12345678901/ansible-fake',
            'conjur_authn_type': 'aws',
            'conjur_authn_service_id': 'aws-service',
        }
        result = lookup.run(['ansible/fake-secret'], variables)

        self.assertEqual(result, ['super_secret_value'])
        mock_fetch_iam_token.assert_called_once()

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_certificate_file')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_variable')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_azure_token')
    def test_run_with_azure_authenticator(self, mock_fetch_azure_token, mock_fetch_variable, mock_get_cert_file):
        mock_get_cert_file.return_value = './conjur.pem'
        mock_fetch_azure_token.return_value = b'conjur-access-token'
        mock_fetch_variable.return_value = ['super_secret_value']

        lookup = lookup_loader.get('cyberark.conjur.conjur_variable')
        variables = {
            'conjur_account': 'fakeaccount',
            'conjur_appliance_url': 'https://conjur-fake',
            'conjur_cert_file': './conjur.pem',
            'conjur_authn_login': 'host/azure/ansible-fake',
            'conjur_authn_type': 'azure',
            'conjur_authn_service_id': 'azure-service',
            'azure_client_id': 'fake-client-id',
        }
        result = lookup.run(['ansible/fake-secret'], variables)

        self.assertEqual(result, ['super_secret_value'])
        mock_fetch_azure_token.assert_called_once()
        self.assertEqual(mock_fetch_azure_token.call_args.kwargs.get('client_id'), 'fake-client-id')

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_certificate_file')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_variable')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_gcp_identity_token')
    def test_run_with_gcp_authenticator(self, mock_fetch_gcp_token, mock_fetch_variable, mock_get_cert_file):
        mock_get_cert_file.return_value = './conjur.pem'
        mock_fetch_gcp_token.return_value = b'conjur-access-token'
        mock_fetch_variable.return_value = ['super_secret_value']

        lookup = lookup_loader.get('cyberark.conjur.conjur_variable')
        variables = {
            'conjur_account': 'fakeaccount',
            'conjur_appliance_url': 'https://conjur-fake',
            'conjur_cert_file': './conjur.pem',
            'conjur_authn_login': 'host/gcp/ansible-fake',
            'conjur_authn_type': 'gcp',
        }
        result = lookup.run(['ansible/fake-secret'], variables)

        self.assertEqual(result, ['super_secret_value'])
        mock_fetch_gcp_token.assert_called_once()


class TestLookupModuleValidation(TestCase):
    """Unit tests for LookupModule.run() input validation and misc branches (CONJ-103)."""

    def setUp(self):
        self.lookup = lookup_loader.get('cyberark.conjur.conjur_variable')

    def test_insecure_http_url_raises(self):
        variables = {
            'conjur_account': 'fakeaccount',
            'conjur_appliance_url': 'http://conjur-fake',
            'conjur_authn_login': 'host/ansible/ansible-fake',
            'conjur_authn_api_key': 'fakekey',
        }
        with self.assertRaises(AnsibleError) as context:
            self.lookup.run(['ansible/fake-secret'], variables)
        self.assertIn("insecure connection", str(context.exception))

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_certificate_file')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_variable')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_token')
    def test_missing_account_defaults_to_conjur(self, mock_fetch_token, mock_fetch_variable, mock_get_cert_file):
        mock_get_cert_file.return_value = None
        mock_fetch_token.return_value = b'token'
        mock_fetch_variable.return_value = ['super_secret_value']

        variables = {
            'conjur_appliance_url': 'https://conjur-fake',
            'conjur_authn_login': 'host/ansible/ansible-fake',
            'conjur_authn_api_key': 'fakekey',
        }
        result = self.lookup.run(['ansible/fake-secret'], variables)

        self.assertEqual(result, ['super_secret_value'])
        self.assertEqual(mock_fetch_token.call_args[0][1], 'conjur')

    def test_missing_service_id_for_aws_raises(self):
        variables = {
            'conjur_account': 'fakeaccount',
            'conjur_appliance_url': 'https://conjur-fake',
            'conjur_authn_login': 'host/aws/12345678901/ansible-fake',
            'conjur_authn_type': 'aws',
        }
        with self.assertRaises(AnsibleError) as context:
            self.lookup.run(['ansible/fake-secret'], variables)
        self.assertIn("conjur_authn_service_id", str(context.exception))

    def test_missing_service_id_for_azure_raises(self):
        variables = {
            'conjur_account': 'fakeaccount',
            'conjur_appliance_url': 'https://conjur-fake',
            'conjur_authn_login': 'host/azure/ansible-fake',
            'conjur_authn_type': 'azure',
        }
        with self.assertRaises(AnsibleError) as context:
            self.lookup.run(['ansible/fake-secret'], variables)
        self.assertIn("conjur_authn_service_id", str(context.exception))

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._get_certificate_file')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_variable')
    def test_run_reads_token_from_authn_token_file(self, mock_fetch_variable, mock_get_cert_file):
        mock_get_cert_file.return_value = None
        mock_fetch_variable.return_value = ['super_secret_value']

        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as token_file:
            token_file.write(b'fake-conjur-token')
            token_path = token_file.name

        try:
            variables = {
                'conjur_account': 'fakeaccount',
                'conjur_appliance_url': 'https://conjur-fake',
                'conjur_authn_token_file': token_path,
            }
            result = self.lookup.run(['ansible/fake-secret'], variables)

            self.assertEqual(result, ['super_secret_value'])
            self.assertEqual(mock_fetch_variable.call_args[0][1], b'fake-conjur-token')
        finally:
            os.unlink(token_path)

    def test_run_missing_authn_token_file_raises(self):
        variables = {
            'conjur_account': 'fakeaccount',
            'conjur_appliance_url': 'https://conjur-fake',
            'conjur_authn_token_file': '/nonexistent/token/file',
        }
        with self.assertRaises(AnsibleError) as context:
            self.lookup.run(['ansible/fake-secret'], variables)
        self.assertIn("was not found on the host", str(context.exception))

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_variable')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_token')
    def test_temp_cert_file_is_removed_after_run(self, mock_fetch_token, mock_fetch_variable):
        mock_fetch_token.return_value = b'token'
        mock_fetch_variable.return_value = ['super_secret_value']

        cert_content = (
            "-----BEGIN CERTIFICATE-----\n"
            "FakeCertData\n"
            "-----END CERTIFICATE-----"
        )
        with patch(
            'ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.default_backend',
            return_value=None, create=True,
        ), patch(
            'ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.load_pem_x509_certificate',
            return_value=None, create=True,
        ):
            variables = {
                'conjur_account': 'fakeaccount',
                'conjur_appliance_url': 'https://conjur-fake',
                'conjur_authn_login': 'host/ansible/ansible-fake',
                'conjur_authn_api_key': 'fakekey',
                'conjur_cert_content': cert_content,
            }
            self.lookup.run(['ansible/fake-secret'], variables)

        temp_cert_path = mock_fetch_token.call_args[0][5]
        self.assertIsNotNone(temp_cert_path)
        self.assertFalse(os.path.exists(temp_cert_path))

    def test_get_var_value_raises_ansible_error_on_unknown_key(self):
        with self.assertRaises(AnsibleError):
            self.lookup.get_var_value('not_a_real_option')


class TestValidateAuthnCertFiles(TestCase):
    """Unit tests for _validate_authn_cert_files() (CONJ-103)."""

    def test_missing_client_cert_raises(self):
        with self.assertRaises(AnsibleError) as context:
            _validate_authn_cert_files(None, '/tmp/fake_client.key')
        self.assertIn("Client certificate file", str(context.exception))

    def test_missing_client_key_raises(self):
        with tempfile.NamedTemporaryFile(delete=False) as cert_file:
            cert_path = cert_file.name
        try:
            with self.assertRaises(AnsibleError) as context:
                _validate_authn_cert_files(cert_path, '/nonexistent/client.key')
            self.assertIn("Client key file", str(context.exception))
        finally:
            os.unlink(cert_path)

    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.display')
    def test_insecure_client_key_permissions_warns(self, mock_display):
        with tempfile.NamedTemporaryFile(delete=False) as cert_file:
            cert_path = cert_file.name
        with tempfile.NamedTemporaryFile(delete=False) as key_file:
            key_path = key_file.name
        try:
            os.chmod(key_path, 0o644)
            _validate_authn_cert_files(cert_path, key_path)
            mock_display.warning.assert_called_once()
            self.assertIn("insecure permissions", mock_display.warning.call_args[0][0])
        finally:
            os.unlink(cert_path)
            os.unlink(key_path)
