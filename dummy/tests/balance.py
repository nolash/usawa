import logging
import unittest
import datetime
import os

from usawa import EntryPart, Entry, UnitIndex
from usawa.balance import Balancer

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.realpath(os.path.dirname(__file__))

class TestBalancer(unittest.TestCase):


    def setUp(self):
        self.parent = bytes.fromhex('0cf9180a764aba863a67b6d72f0918bc131c6772642cb2dce5a34f0a702f9470ddc2bf125c12198b1995c233c34b4afd346c54a2334c350a948a51b6e8b4e6b6')
        self.ref = '1bda7dfa-b8fd-400d-8b42-1d2861ad7f70'
        self.uidx = UnitIndex('FOO')
        self.uidx.add('BAR', 3)
        self.description = "foo bar baz"
        self.dtreg = datetime.datetime.now()


    def test_balancer_parts_simple(self):
        o = Balancer(self.uidx)
        src = EntryPart('FOO.Income/baz', 1337, debit=True)
        o.apply_part(src)
        dst = EntryPart('FOO.Asset/foo', 1337)
        o.apply_part(dst)
        self.assertTrue(o.balanced())


    def test_balancer_parts_exchange(self):
        o = Balancer(self.uidx)
        self.uidx.set_rate('BAR', 230000000)
        src = EntryPart('BAR.Income/baz', 420000, debit=True)
        o.apply_part(src)
        dst = EntryPart('FOO.Asset/foo', 9660)
        o.apply_part(dst)
        self.assertTrue(o.balanced())


    def test_balance_accumulate_simple(self):
        o = Balancer(self.uidx)
        src = EntryPart('FOO.Asset/baz', -1337, debit=True)
        o.apply_part(src)
        dst = EntryPart('FOO.Asset/foo', 1337)
        o.apply_part(dst)
        self.assertTrue(o.balanced())
        self.assertEqual(o.value(), 1337)

        o = Balancer(self.uidx)
        src = EntryPart('FOO.Liability/baz', 1337, debit=True)
        o.apply_part(src)
        dst = EntryPart('FOO.Asset/foo', 1337)
        o.apply_part(dst)
        self.assertTrue(o.balanced())
        self.assertEqual(o.value(), 1337)

        o = Balancer(self.uidx)
        src = EntryPart('FOO.Liability/baz', 1337, debit=True)
        o.apply_part(src)
        dst = EntryPart('FOO.Liability/foo', -1337)
        o.apply_part(dst)
        self.assertTrue(o.balanced())
        self.assertEqual(o.value(), 1337)

        o = Balancer(self.uidx)
        src = EntryPart('FOO.Asset/baz', -1337, debit=True)
        o.apply_part(src)
        dst = EntryPart('FOO.Liability/foo', -1337)
        o.apply_part(dst)
        self.assertTrue(o.balanced())
        self.assertEqual(o.value(), 1337)


    def test_flow_accumulate_simple(self):
        o = Balancer(self.uidx)
        src = EntryPart('FOO.Asset/baz', -1337, debit=True)
        o.apply_part(src)
        dst = EntryPart('FOO.Expense/foo', 1337)
        o.apply_part(dst)
        self.assertTrue(o.balanced())
        self.assertEqual(o.value(), 1337)

        o = Balancer(self.uidx)
        src = EntryPart('FOO.Income/baz', 1337, debit=True)
        o.apply_part(src)
        dst = EntryPart('FOO.Asset/foo', 1337)
        o.apply_part(dst)
        self.assertTrue(o.balanced())
        self.assertEqual(o.value(), 1337)

        o = Balancer(self.uidx)
        src = EntryPart('FOO.Income/baz', 1337, debit=True)
        o.apply_part(src)
        dst = EntryPart('FOO.Expense/foo', 1337)
        o.apply_part(dst)
        self.assertTrue(o.balanced())
        self.assertEqual(o.value(), 1337)

        o = Balancer(self.uidx)
        src = EntryPart('FOO.Income/baz', 1337, debit=True)
        o.apply_part(src)
        dst = EntryPart('FOO.Liability/foo', -1337)
        o.apply_part(dst)
        self.assertTrue(o.balanced())
        self.assertEqual(o.value(), 1337)


    def test_balance_running(self):
        o = Balancer(self.uidx)
        src = EntryPart('FOO.Liability/foo', 1337, debit=True)
        o.apply_part(src)
        self.assertEqual(o.balance(), -1337)

        dst = EntryPart('FOO.Asset/bar', 42)
        o.apply_part(dst)
        self.assertEqual(o.balance(), -1295)

        dst = EntryPart('FOO.Expense/baz', 1295)
        o.apply_part(dst)
        self.assertTrue(o.balanced())
        self.assertEqual(o.value(), 1337)


if __name__ == '__main__':
    unittest.main()
