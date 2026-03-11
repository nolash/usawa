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
        # missing account type
        with self.assertRaises(AttributeError):
            idx.add('bar/baz', sym='FOO')
        idx.add('liability/bar/baz', sym='FOO')
        idx.add('liability/bar/baz', sym='FOO')
        with self.assertRaises(AccountError):
            idx.add('asset/bar/baz-', sym='FOO')
        with self.assertRaises(AccountError):
            idx.add('asset/foo/bar', sym='BAZ')
        self.assertFalse(idx.check('BAR', 'liability/foo/baz'))
        self.assertTrue(idx.check('FOO', 'liability/bar/baz'))


    def test_account_list(self):
        idx = AccountIndex(self.uidx)
        idx.add('asset/bar/bar', sym='FOO')
        idx.add('liability/bar/baz', sym='FOO')
        idx.add('asset/foo/baz', sym='BAR')
        v = list(idx)
        logg.debug('results {}'.format(v))
        self.assertEqual(len(v), 3)


if __name__ == '__main__':
    unittest.main()
