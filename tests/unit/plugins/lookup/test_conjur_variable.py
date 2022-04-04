from __future__ import absolute_import, division, print_function
# from cProfile import run
from lib2to3.pgen2 import token
from ansible.plugins.lookup import LookupBase
__metaclass__ = type

from ansible_collections.cyberark.conjur.tests.unit.compat.unittest import TestCase
from ansible_collections.cyberark.conjur.tests.unit.compat.mock import patch , MagicMock
from ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable import _merge_dictionaries, _fetch_conjur_token , _fetch_conjur_variable , LookupModule , _load_identity_from_file , _load_conf_from_file
from ansible.plugins.loader import lookup_loader
 # from ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.LookupModule import run
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
        mock_response.read.decode("utf-8").return_value = "response body"
       # mock_response.read.decode().return_value = "response body"
        mock_repeat_open_url.return_value = mock_response
        result = _fetch_conjur_variable("variable", b'{"protected":"eykhRJ"}', "url", "account", True, "cert_file")
        mock_repeat_open_url.assert_called_with("url/secrets/account/variable/variable",
                                                headers={'Authorization': 'Token token="eyJwcm90ZWN0ZWQiOiJleWtoUkoifQ=="'},
                                                method="GET",
                                                validate_certs=True,
                                                ca_path="cert_file")
        # self.assertEquals("response body", result)


    @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.LookupBase')
    def test_run(self, mock_LookupBase):
        mock_response = MagicMock()
        mock_response.return_value = ['test_secret_password']
        mock_LookupBase.return_value = mock_response
        result = LookupBase.run(['ansible/test-secret'],None,{})
        # mock_LookupBase.assert_called_with("url/authn/account/username/authenticate",
        #                                  data="api_key",
        #                                  method="POST",
        #                                  validate_certs=True,
        #                                  ca_path="cert_file")
        #self.assertEquals("['test_secret_password']", result)

        self.assertEquals(None, result)




    # 1-

    # @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._repeat_open_url')
    # def test_fetch_conjur_variable(self, mock_repeat_open_url):
    #     mock_response = MagicMock()
    #     mock_response.getcode.return_value = 200
    #     mock_response.read.decode("utf-8").return_value = "response body"
    #    # mock_response.read.decode().return_value = "response body"
    #     mock_repeat_open_url.return_value = mock_response
    #     result = _fetch_conjur_variable("variable", b'{"protected":"eykhRJ"}', "url", "account", True, "cert_file")
    #     mock_repeat_open_url.assert_called_with("url/secrets/account/variable/variable",
    #                                             headers={'Authorization': 'Token token="eyJwcm90ZWN0ZWQiOiJleWtoUkoifQ=="'},
    #                                             method="GET",
    #                                             validate_certs=True,
    #                                             ca_path="cert_file")
    #     # self.assertEquals("response body", result)

    # 2-
    # @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable._fetch_conjur_variable')
    # def test_run(self, mock_fetch_conjur_variable):
    #     mock_response = MagicMock()
    #     mock_response.return_value = ['test_secret_password']
    #     mock_fetch_conjur_variable.return_value = mock_response
    #     result = run(LookupBase)
    #     mock_fetch_conjur_variable.assert_called_with("variable", b'{"protected":"eykhRJ"}', "url", "account", True, "cert_file")
    #     self.assertEquals(['test_secret_password'], result)

    # 3-
        # def test_fetch_conjur_variable(self):
        # load_conf= _fetch_conjur_variable("ansible/test-secret",
        #                                 b'{"protected":"eyJhbGciOiJjb25qdXIub3JnL3Nsb3NpbG8vdjIiLCJraWQiOiIyNTY2ZmZkYzljY2ZiODBiNWZiMDE4YjVjMDkxOGQ2MTVlZjJkMGI3MzcwZmQ2NmE5NjVjNzUwNmJlNzVlZmY0In0=","payload":"eyJzdWIiOiJob3N0L2Fuc2libGUvYW5zaWJsZS1tYXN0ZXIiLCJpYXQiOjE2NDg3OTExMzh9","signature":"sL3nvwBWXnTqTrF9ueFcUDAT5-ALa6ptByQ2Kk9ON80GumdgqeZYQxBmln-JSq22gxLl63tlF_pJ4rOCBoOG6SsOmlqROqD4IyDVzqMYmV39b7CEqRnu7jehF2fKuyu5x2MmCp5cuswgj8Yf9NEmBYOq9zEjvgGCrOaKqEItaHHKbPiyo6OwMqbL51C1vfC6E4Qiixmr37xMooC-OWfanppgtzszSN-spFOPl0JbCJT5-p0DaN3Gj94ZEDPcmERSOWGCzPJHsaFh293TDWpX3B6P5AAoKi-gRymJk3zLQY7Vg6_-EPhYyogZMBPX3A3ndaiz2veFWA_81FDCd3tCyY_x7pBLeBsvCVD8EUZwcLD2DLT0X_1GKWe1MxRP6hrC"}',
        #                                 "https://conjur-https",
        #                                 "cucumber",
        #                                 True,
        #                                 "/Users/Pooja.Gangwar/Github_UT/ansible_collections/cyberark/conjur/tests/unit/plugins/lookup/conjur.pem")
        #                                 #"/ansible_collections/cyberark/conjur/tests/unit/plugins/lookup/conjur.pem")
        # self.assertEquals(MockSecretsVault_a.RESPONSE,load_conf)



    # @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.os.path')
    # def test_load_identity_from_file(self, mock_path):
    #     mock_response = MagicMock()
    #     mock_response.return_value = {}
    #     # mock_response.read.return_value = "response body"
    #     mock_path.return_value = mock_response
    #     result = _load_identity_from_file("/etc/conjur.identity", "https://conjur-https")
    #     mock_path.assert_called_with("/etc/conjur.identity")
    #     self.assertEquals({}, result)



    # @patch('ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable.LookupModule.run', MockSecretsVault1())
    # def test_run(self , mock_run):
    #     mock_response = MagicMock()
    #     mock_response.getcode.return_value = 200
    #     expected_result = ['test_secret_password']
    #     field = kwargs.get('field', 'password')
    #     self.assertListEqual(expected_result, LookupModule.run(['ansible/test-secret'],None,{'validate_certs','config_file','as_file'}))

        # thisdict = {
        # "validate_certs": "validate_certs",
        # "conf_file": "conf_file",
        # "as_file": "as_file"
        # }
           # (['ansible/test-secret'],None,thisdict)
