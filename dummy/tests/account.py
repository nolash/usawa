import logging
import datetime
import unittest
import os

from usawa import UnitIndex
from usawa.account import AccountIndex
from usawa.error import AccountError

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.realpath(os.path.dirname(__file__))

class TestAccount(unittest.TestCase):

    def setUp(self):
        self.uidx = UnitIndex('FOO')
        self.uidx.add('BAR')

    def test_account_lock(self):
        idx = AccountIndex(self.uidx)
        idx.add('FOO', 'bar.baz')
        idx.add('FOO', 'bar.baz')
        with self.assertRaises(AccountError):
            idx.add('FOO', 'bar.baz-')
        with self.assertRaises(AccountError):
            idx.add('BAZ', 'foo.bar')
        self.assertFalse(idx.check('BAR', 'foo.baz'))
        self.assertTrue(idx.check('FOO', 'bar.baz'))


    def test_account_list(self):
        idx = AccountIndex(self.uidx)
        idx.add('FOO', 'bar.bar')
        idx.add('FOO', 'bar.baz')
        idx.add('BAR', 'foo.baz')
        v = list(idx)
        logg.debug('results {}'.format(v))
        self.assertEqual(len(v), 3)


if __name__ == '__main__':
    unittest.main()
