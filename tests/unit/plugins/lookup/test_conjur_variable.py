from __future__ import absolute_import, division, print_function
from lib2to3.pgen2 import token
from unittest import result
__metaclass__ = type

from ansible_collections.cyberark.conjur.tests.unit.compat.unittest import TestCase
from ansible_collections.cyberark.conjur.tests.unit.compat.mock import patch , MagicMock, call
from ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable import _merge_dictionaries, _fetch_conjur_token , _fetch_conjur_variable , LookupModule , _load_identity_from_file , _load_conf_from_file
from ansible.plugins.loader import lookup_loader
from ansible.plugins.lookup import LookupBase

class MockMergeDictionaries(MagicMock):
    RESPONSE = {'id': 'host/ansible/ansible-master', 'api_key': '1j8t1rx2ghwhx7392wt1h14qn3c22yp4w2y395yk9d2hz8gvb1nbh6yg'}

class MockFileload(MagicMock):
    RESPONSE = {}

class TestConjurLookup(TestCase):
    def setUp(self):
        self.lookup = lookup_loader.get("conjur_variable")
        assert(self.lookup != None)

    #@patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._merge_dictionaries',MockSecretsVault())
    def test_merge_dictionaries(self):
        functionOutput= _merge_dictionaries(
            {},
            {'id': 'host/ansible/ansible-master', 'api_key': '1j8t1rx2ghwhx7392wt1h14qn3c22yp4w2y395yk9d2hz8gvb1nbh6yg'}
        )
        self.assertEquals(MockMergeDictionaries.RESPONSE,functionOutput)

    def test_load_identity_from_file(self):
        load_identity= _load_identity_from_file("/etc/conjur.identity","https://conjur-https")
        self.assertEquals(MockFileload.RESPONSE,load_identity)

    def test_load_conf_from_file(self):
        load_conf= _load_conf_from_file("/etc/conjur.conf")
        self.assertEquals(MockFileload.RESPONSE,load_conf)

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
        self.assertEquals("response body", result)


    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._repeat_open_url')
    def test_fetch_conjur_variable(self, mock_repeat_open_url):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = "response body".encode("utf-8")
        mock_repeat_open_url.return_value = mock_response
        result = _fetch_conjur_variable("variable", b'{"protected":"eykhRJ"}', "url", "account", True, "cert_file")
        mock_repeat_open_url.assert_called_with("url/secrets/account/variable/variable",
                                                headers={'Authorization': 'Token token="eyJwcm90ZWN0ZWQiOiJleWtoUkoifQ=="'},
                                                method="GET",
                                                validate_certs=True,
                                                ca_path="cert_file")
        self.assertEquals(['response body'], result)


    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_variable')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_token')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._merge_dictionaries')
    def test_run(self,
        mock_merge_dictionaries ,
        mock_fetch_conjur_token ,
        mock_fetch_conjur_variable):

        mock_fetch_conjur_token.return_value = "token"
        mock_fetch_conjur_variable.return_value = 'test_secret_password'

        mock_merge_dictionaries.side_effect = [
            {'account': 'cucumber', 'appliance_url': 'https://conjur-https', 'cert_file': './conjur.pem'},
            {'id': 'host/ansible/ansible-master', 'api_key': '37rdyqz56b2dd2v4px501zfqxb18xxbpw339rtav11rdzmv25ck70b'}
        ]

        terms = ['ansible/test-secret']
        kwargs = {'as_file': False, 'conf_file': 'conf_file', 'validate_certs': False}
        result = self.lookup.run(terms, **kwargs)

        self.assertEquals(result, 'test_secret_password')
        mock_fetch_conjur_token.assert_called_with('https://conjur-https', 'cucumber', 'host/ansible/ansible-master', '37rdyqz56b2dd2v4px501zfqxb18xxbpw339rtav11rdzmv25ck70b', False, './conjur.pem')
        mock_fetch_conjur_variable.assert_called_with('ansible/test-secret', 'token', 'https://conjur-https', 'cucumber', False, './conjur.pem')
        mock_merge_dictionaries.assert_has_calls([
            call({}, {}, {}, {}),
            call({}, {})
        ],any_order=False)
