import logging
import datetime
import unittest
import os

from usawa import UnitIndex
from usawa.account import AccountIndex, AccountType, AccountDisplay
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
        self.assertFalse(idx.check('BAR', AccountType.liability, 'foo/baz'))
        self.assertTrue(idx.check('FOO', AccountType.liability, 'bar/baz'))


    def test_account_list(self):
        idx = AccountIndex(self.uidx)
        idx.add('asset/bar/bar', sym='FOO')
        idx.add('liability/bar/baz', sym='FOO')
        idx.add('asset/foo/baz', sym='BAR')
        v = list(idx)
        self.assertEqual(len(v), 3)


    def test_account_filter(self):
        idx = AccountIndex(self.uidx)
        idx.add('asset/bar/bar', sym='FOO')
        idx.add('liability/bar/baz', sym='FOO')
        idx.add('asset/foo/baz', sym='BAR')
        idx.add('asset/xyzzy', sym='BAR')
        idx.set_filter(sym='FOO')
        v = list(idx)
        self.assertEqual(len(v), 2)
        idx.set_filter(sym='BAR')
        v = list(idx)
        self.assertEqual(len(v), 2)
        idx.set_filter(sym='FOO', typ=AccountType.liability)
        v = list(idx)
        self.assertEqual(len(v), 1)
        idx.set_filter(sym='BAR', typ=AccountType.asset)
        v = list(idx)
        self.assertEqual(len(v), 2)


    def test_account_display(self):
        idx = AccountIndex(self.uidx)
        idx.add('asset/bar/baz', sym='FOO')
        v = list(idx)
        self.assertEqual(v[0], 'FOO.asset/bar/baz')
        idx.set_filter(display=AccountDisplay.typ)
        v = list(idx)
        self.assertEqual(v[0], 'asset/bar/baz')
        idx.set_filter(display=AccountDisplay.path)
        v = list(idx)
        self.assertEqual(v[0], 'bar/baz')


if __name__ == '__main__':
    unittest.main()
