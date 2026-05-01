import logging
import datetime
import unittest
import os

from whee.mem import MemStore

from usawa import UnitIndex
from usawa import Ledger, UnitIndex, EntryPart, Entry, DemoWallet, ACL, schema_path
from usawa.store import LedgerStore
from usawa.account import AccountIndex, AccountType, AccountDisplay
from usawa.error import AccountError
from usawa.index.account import EntryAccountIndex

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.realpath(os.path.dirname(__file__))

class TestIndex(unittest.TestCase):


    def setUp(self):
        self.store = MemStore()
        self.eidx = EntryAccountIndex()


    def test_accountsindex(self):
        s = 'FOO'
        uidx = UnitIndex(s)
        wallet = DemoWallet()
        o = Ledger(uidx, wallet=wallet)
        o.register_callback(self.eidx.entry_callback)
        store = LedgerStore(self.store, ledger=o)
        store.start()


        x = EntryPart(s, 'income', 'foo', 1337, debit=True)
        y = EntryPart(s, 'asset', 'foo', 1337)
        v = Entry(o.peek(), datetime.datetime.now(), parent=o.current())
        v.add_part(x)
        v.add_part(y)
        v.sign(wallet)
        store.add_entry(v, update_ledger=True)

        x = EntryPart(s, 'expense', 'bar', 42, debit=True)
        y = EntryPart(s, 'liability', 'bar', 42)
        v = Entry(o.peek(), datetime.datetime.now(), parent=o.current())
        v.add_part(x)
        v.add_part(y)
        v.sign(wallet)
        store.add_entry(v, update_ledger=True)

        x = EntryPart(s, 'expense', 'bar', 42, debit=True)
        y = EntryPart(s, 'liability', 'bar', 42)
        v = Entry(o.peek(), datetime.datetime.now(), parent=o.current())
        v.add_part(x)
        v.add_part(y)
        v.sign(wallet)
        store.add_entry(v, update_ledger=True)

        self.eidx.start('FOO.income/foo')
        r = list(self.eidx)
        self.assertEqual(len(r), 1)
        entry = Entry.empty(serial=r[0])
        entry = store.get_entry(entry)

        self.eidx.start('FOO.expense/bar')
        r = list(self.eidx)
        self.assertEqual(len(r), 2)
        for v in r:
            entry = Entry.empty(serial=v)
            entry = store.get_entry(entry)



if __name__ == '__main__':
    unittest.main()
