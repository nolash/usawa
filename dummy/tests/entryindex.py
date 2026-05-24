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
        self.wallet = DemoWallet()

        dst = EntryPart('FOO.Asset/foo', 1337)
        src = EntryPart('FOO.Income/foo', 1337, debit=True)
        self.entry_a = Entry(1, datetime.datetime.strptime('2025-11-11', '%Y-%m-%d'), ref=str(uuid.uuid4()), description='foo', unitindex=self.uidx)
        o = self.entry_a
        o.add_part(src)
        o.add_part(dst)
        o.sign(self.wallet)
        self.ledger.add_entry(o)

        dst = EntryPart('FOO.Expense/bar', 42)
        src = EntryPart('FOO.Asset/bar', -42, debit=True)
        now = datetime.datetime.now(datetime.UTC)
        self.entry_b = Entry(2, now, parent=self.ledger.cur, ref=str(uuid.uuid4()), description='bar', unitindex=self.uidx)
        o = self.entry_b
        o.add_part(src)
        o.add_part(dst)
        o.sign(self.wallet)
        self.ledger.add_entry(o)


    def test_entry_check_index(self):
        r = self.eidx.get_ref(self.entry_a)
        self.assertEqual(r, self.entry_a.ref)
        r = self.eidx.get_digest(self.entry_a)
        z = self.entry_a.sum()
        self.assertEqual(r, z[0])

        r = self.eidx.get_ref(self.entry_b)
        self.assertEqual(r, self.entry_b.ref)
        r = self.eidx.get_digest(self.entry_b)
        z = self.entry_b.sum()
        self.assertEqual(r, z[0])


    def test_entry_export(self):
        o = self.eidx.to_tree()
        idx = EntryIndex.from_tree(o)
        r = idx.get_ref(1)
        self.assertEqual(r, self.entry_a.ref)
        r = idx.get_ref(2)
        self.assertEqual(r, self.entry_b.ref)
        z = self.entry_a.sum()[0]
        r = idx.get_digest(1)
        self.assertEqual(r, z)
        z = self.entry_b.sum()[0]
        r = idx.get_digest(2)
        self.assertEqual(r, z)


if __name__ == '__main__':
    unittest.main()


if __name__ == '__main__':
    unittest.main()
