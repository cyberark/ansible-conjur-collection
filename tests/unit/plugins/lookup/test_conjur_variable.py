from __future__ import absolute_import, division, print_function
# from cProfile import run
from lib2to3.pgen2 import token
from unittest import result
from ansible.plugins.lookup import LookupBase
__metaclass__ = type

from ansible_collections.cyberark.conjur.tests.unit.compat.unittest import TestCase
from ansible_collections.cyberark.conjur.tests.unit.compat.mock import patch , MagicMock
from ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable import _merge_dictionaries, _fetch_conjur_token , _fetch_conjur_variable , LookupModule , _load_identity_from_file , _load_conf_from_file
from ansible.plugins.loader import lookup_loader
from ansible.plugins.lookup import LookupBase
# from base64 import b64encode

class MockMergeDictionaries(MagicMock):
    RESPONSE = {'id': 'host/ansible/ansible-master', 'api_key': '1j8t1rx2ghwhx7392wt1h14qn3c22yp4w2y395yk9d2hz8gvb1nbh6yg'}

    def get_secret_json(self, path):
        return self.RESPONSE

class MockFileload(MagicMock):
    RESPONSE = {}

    def get_secret_json2(self, path):
        return self.RESPONSE

class Test(TestCase):
    def setUp(self):
        self.lookup = lookup_loader.get("plugins.lookup.conjur_variable")

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



    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._repeat_open_url')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_variable')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_token')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._load_identity_from_file')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._load_conf_from_file')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._merge_dictionaries')
    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.LookupModule')
    def test_run(self,
        mock_LookupModule ,
        mock_merge_dictionaries ,
        mock_load_conf_from_file ,
        mock_load_identity_from_file ,
        mock_fetch_conjur_token ,
        mock_fetch_conjur_variable,
        mock_repeat_open_url):

        mock_response = MagicMock()
        mock_response.return_value = ['test_secret_password']
        mock_LookupModule.return_value = mock_response

        self = mock_LookupModule
        terms = ['ansible/test-secret']
        variables = None
        kwargs = {'as_file': 'as_file', 'conf_file': 'conf_file', 'validate_certs': 'validate_certs'}
        # result = LookupModule.run(self, terms, variables, **kwargs)






        # self.assertEquals(None, result)

    #     # ============_merge_dictionaries========
    #     result_merge_dictionaries = _merge_dictionaries(
    #         {},
    #         {'id': 'host/ansible/ansible-master', 'api_key': '1j8t1rx2ghwhx7392wt1h14qn3c22yp4w2y395yk9d2hz8gvb1nbh6yg'}
    #     )

    #     # ============_load_conf_from_file========
    #     result__load_conf_from_file = _load_conf_from_file("/etc/conjur.conf")

    #     # ====================_load_identity_from_file======
    #     result_load_identity_from_file = _load_identity_from_file("/etc/conjur.identity","https://conjur-https")

    #     # ================================_fetch_conjur_variable==================
    #     mock_response.getcode.return_value = 200
    #     mock_response.read.return_value = "response body".encode("utf-8")
    #     mock_repeat_open_url.return_value = mock_response
    #     result_fetch_conjur_variable = _fetch_conjur_variable("variable", b'{"protected":"eykhRJ"}', "url", "account", True, "cert_file")
    #     mock_repeat_open_url.assert_called_with("url/secrets/account/variable/variable",
    #                                             headers={'Authorization': 'Token token="eyJwcm90ZWN0ZWQiOiJleWtoUkoifQ=="'},
    #                                             method="GET",
    #                                             validate_certs=True,
    #                                             ca_path="cert_file")

    #     # ==================================================
