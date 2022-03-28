from __future__ import absolute_import, division, print_function
__metaclass__ = type

import unittest
from ansible_collections.cyberark.conjur.plugins.lookup.conjur_variable import (
    LookupModule,
)


class TestStringMethods(unittest.TestCase):

    def setUp(self):
        self._lp = LookupModule()
        # self._lp._load_name = "conjur_variable"

    def test_upper(self):
        self.assertEqual('foo'.upper(), 'FOO')

    def test_isupper(self):
        self.assertTrue('FOO'.isupper())
        self.assertFalse('Foo'.isupper())

    def test_split(self):
        s = 'hello world'
        self.assertEqual(s.split(), ['hello', 'world'])
        # check that s.split fails when the separator is not a string
        with self.assertRaises(TypeError):
            s.split(2)

    # def test_valid_data(self):
    #    """Check passing valid data as per criteria"""
    #    terms = ['ansible/test-secret']
    #    kwargs = {}
    #    #variables = 'None'
    #    result = self._lp.run(terms, variables=None, **kwargs)
    #    self.assertEquals(result, ['test_secret_password'])


if __name__ == '__main__':
    unittest.main()
