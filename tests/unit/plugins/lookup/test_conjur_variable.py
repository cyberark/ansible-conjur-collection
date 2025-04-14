from __future__ import absolute_import, division, print_function
__metaclass__ = type

import hashlib
import hmac
import json
from ansible.module_utils.six.moves import urllib_error
from unittest import TestCase
from unittest.mock import MagicMock, patch, mock_open
from ansible.errors import AnsibleError
from ansible.plugins.loader import lookup_loader
from base64 import b64encode

from ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable import _merge_dictionaries, _fetch_conjur_token, _fetch_conjur_variable, \
    _validate_pem_certificate, _load_identity_from_file, _load_conf_from_file, _telemetry_header, \
    _valid_aws_account_number, _sign, _get_signature_key, _get_aws_region, \
    _get_metadata_token, _get_iam_role_metadata, _create_canonical_request, \
    _create_conjur_iam_api_key, _get_iam_role_name, _fetch_conjur_iam_session_token, \
    InvalidAwsAccountIdException, ConjurIAMAuthnException, _fetch_conjur_azure_token, \
    _fetch_conjur_gcp_identity_token


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
            ca_path="cert_file"
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

    def test_run_telemetry_header(self):
        with patch('builtins.open', mock_open(read_data='1.0.0')), \
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
    def test_fetch_conjur_iam_session_token_success(self, mock_create_conjur_iam_api_key, mock_telemetry_header, mock_valid_account, mock_open_url):
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
    def test_fetch_conjur_iam_session_token_auth_failure(self, mock_create_conjur_iam_api_key, mock_telemetry_header, mock_valid_account, mock_open_url):
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
    def test_fetch_conjur_iam_session_token_http_error(self, mock_create_conjur_iam_api_key, mock_telemetry_header, mock_valid_account, mock_open_url):
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
    def test_fetch_conjur_gcp_identity_token_failure(self, mock_open_url, mock_telemetry_header):
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
    def test_gcp_authenticate_endpoint_failure(self, mock_open_url, mock_telemetry_header):
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
