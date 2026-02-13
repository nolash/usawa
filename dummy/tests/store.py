import logging
import datetime
import unittest
import os
import copy
import uuid

import lxml.etree
from whee.mem import MemStore

from usawa import Ledger, UnitIndex, EntryPart, Entry, DemoWallet, Asset
from usawa.store import LedgerStore
from usawa.crypto import ACL

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.realpath(os.path.dirname(__file__))


class TestStore(unittest.TestCase):
    
    def setUp(self):
        self.store = MemStore()
        self.parent = bytes.fromhex('0cf9180a764aba863a67b6d72f0918bc131c6772642cb2dce5a34f0a702f9470ddc2bf125c12198b1995c233c34b4afd346c54a2334c350a948a51b6e8b4e6b6')
        self.ref = '1bda7dfa-b8fd-400d-8b42-1d2861ad7f70'
        self.description = "foo bar baz"
        self.dtreg = datetime.datetime.now()


    def test_store_entry(self):
        uidx = UnitIndex('FOO')
        ledger = Ledger(uidx, serial=42, base=self.parent)
        store = LedgerStore(self.store, ledger)
        dst = EntryPart('FOO', 'asset', 'foo', 1337)
        src = EntryPart('FOO', 'income', 'foo', 1337, debit=True)
        o = Entry(42, datetime.datetime.strptime('2025-11-11', '%Y-%m-%d'), parent=self.parent, ref=self.ref, description=self.description, tx_datereg=self.dtreg, unitindex=uidx)
        o.add_part(src, debit=True)
        o.add_part(dst)
        wallet = DemoWallet()
        o.sign(wallet)
        store.add_entry(o)

        acl = ACL.from_wallet(wallet)
        r = store.get_entry(o.serial, acl=acl)
        self.assertEqual(r.ref, o.ref)
        self.assertEqual(r.description, o.description)


    def test_store_entry_attach(self):
        uidx = UnitIndex('FOO')
        ledger = Ledger(uidx, serial=42, base=self.parent)
        store = LedgerStore(self.store, ledger)
        dst = EntryPart('FOO', 'asset', 'foo', 1337)
        src = EntryPart('FOO', 'income', 'foo', 1337, debit=True)
        o = Entry(42, datetime.datetime.strptime('2025-11-11', '%Y-%m-%d'), parent=self.parent, ref=self.ref, description=self.description, tx_datereg=self.dtreg, unitindex=uidx)
        o.add_part(src, debit=True)
        o.add_part(dst)

        fp = os.path.join(testdir, 'test.xml')
        asset = Asset.from_file(fp, description='foobar')
        store.add_asset(asset)
        o.attach(asset)

        wallet = DemoWallet()
        o.sign(wallet)
        store.add_entry(o)

        acl = ACL.from_wallet(wallet)
        r = store.get_entry(o.serial, acl=acl)
        self.assertEqual(r.ref, o.ref)
        self.assertEqual(r.description, o.description)
        self.assertEqual(r.attachment[0].description, 'foobar')


    def test_store_ledger(self):
        uidx = UnitIndex('FOO')
        wallet = DemoWallet()
        acl = ACL.from_wallet(wallet)
        ledger = Ledger(uidx, serial=41, base=self.parent, acl=acl, wallet=wallet)
        store = LedgerStore(self.store, ledger)

        dst = EntryPart('FOO', 'asset', 'foo', 1337)
        src = EntryPart('FOO', 'income', 'foo', 1337, debit=True)
        o = Entry(ledger.next_serial(), datetime.datetime.strptime('2025-11-11', '%Y-%m-%d'), parent=self.parent, ref=self.ref, description=self.description, tx_datereg=self.dtreg, unitindex=uidx)
        o.add_part(src, debit=True)
        o.add_part(dst)
        o.sign(wallet)
        store.add_entry(o)
    
        ref = str(uuid.uuid4())
        parent = o.sum()[0]
        description = 'barbarbar'
        dtreg = datetime.datetime.now()
        dst = EntryPart('FOO', 'expense', 'bar', 4200)
        src = EntryPart('FOO', 'liability', 'bar', 4200, debit=True)
        o = Entry(ledger.next_serial(), datetime.datetime.strptime('2025-11-12', '%Y-%m-%d'), parent=parent, ref=ref, description=description, tx_datereg=dtreg, unitindex=uidx)
        o.add_part(src, debit=True)
        o.add_part(dst)
        o.sign(wallet)
        store.add_entry(o)

        ledger.sign()
        store.load(acl=acl)


if __name__ == '__main__':
    unittest.main()
