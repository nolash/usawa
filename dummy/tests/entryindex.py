import logging
import datetime
import unittest
import os
import uuid

from usawa import Ledger, UnitIndex, EntryPart, Entry, DemoWallet
from usawa.store import LedgerStore
from usawa.error import AccountError
from usawa.index import EntryIndex

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.realpath(os.path.dirname(__file__))

class TestEntryIndex(unittest.TestCase):

    def setUp(self):
        self.eidx = EntryIndex(digest=True)
        self.uidx = UnitIndex('FOO')
        self.ledger = Ledger(self.uidx, topic=b'bar', entry_index=self.eidx)


    def test_entry_index(self):
        wallet = DemoWallet()

        dst = EntryPart('FOO.Asset/foo', 1337)
        src = EntryPart('FOO.Income/foo', 1337, debit=True)
        entry_a = Entry(1, datetime.datetime.strptime('2025-11-11', '%Y-%m-%d'), ref=str(uuid.uuid4()), description='foo', unitindex=self.uidx)
        o = entry_a
        o.add_part(src)
        o.add_part(dst)
        o.sign(wallet)
        self.ledger.add_entry(o)

        dst = EntryPart('FOO.Expense/bar', 42)
        src = EntryPart('FOO.Asset/bar', -42, debit=True)
        now = datetime.datetime.now(datetime.UTC)
        entry_b = Entry(2, now, parent=self.ledger.cur, ref=str(uuid.uuid4()), description='bar', unitindex=self.uidx)
        o = entry_b
        o.add_part(src)
        o.add_part(dst)
        o.sign(wallet)
        self.ledger.add_entry(o)

        r = self.eidx.get_ref(entry_a)
        self.assertEqual(r, entry_a.ref)
        r = self.eidx.get_digest(entry_a)
        self.assertEqual(r, entry_a.sum())

        r = self.eidx.get_ref(entry_b)
        self.assertEqual(r, entry_b.ref)
        r = self.eidx.get_digest(entry_b)
        self.assertEqual(r, entry_b.sum())


if __name__ == '__main__':
    unittest.main()
