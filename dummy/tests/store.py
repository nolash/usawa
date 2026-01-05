import logging
import datetime
import unittest
import os
import copy
import uuid

import lxml.etree
from whee.mem import MemStore

from usawa import Ledger, UnitIndex, EntryPart, Entry, DemoWallet
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
        uidx = UnitIndex('USD')
        ledger = Ledger(uidx, serial=42, base=self.parent)
        store = LedgerStore(self.store, ledger)
        dst = EntryPart('asset', 'foo', 1337)
        src = EntryPart('income', 'foo', 1337, src=True)
        o = Entry(src, dst, 'USD', 42, datetime.datetime.strptime('2025-11-11', '%Y-%m-%d'), parent=self.parent, ref=self.ref, description=self.description, tx_datereg=self.dtreg)
        wallet = DemoWallet()
        o.sign(wallet)
        store.add_entry(o)
        r = store.get_entry(o.serial)
        self.assertEqual(r.ref, o.ref)
        self.assertEqual(r.description, o.description)


    def test_store_ledger(self):
        uidx = UnitIndex('USD')
        wallet = DemoWallet()
        acl = ACL()
        acl.add(wallet.pubkey())
        ledger = Ledger(uidx, serial=42, base=self.parent)
        store = LedgerStore(self.store, ledger)

        dst = EntryPart('asset', 'foo', 1337)
        src = EntryPart('income', 'foo', 1337, src=True)
        o = Entry(src, dst, 'USD', 42, datetime.datetime.strptime('2025-11-11', '%Y-%m-%d'), parent=self.parent, ref=self.ref, description=self.description, tx_datereg=self.dtreg)
        o.sign(wallet)
        store.add_entry(o)
    
        ref = str(uuid.uuid4())
        parent = o.sum()[0]
        description = 'barbarbar'
        dtreg = datetime.datetime.now()
        dst = EntryPart('expense', 'bar', 4200)
        src = EntryPart('liability', 'bar', 4200, src=True)
        o = Entry(src, dst, 'USD', 43, datetime.datetime.strptime('2025-11-12', '%Y-%m-%d'), parent=parent, ref=ref, description=description, tx_datereg=dtreg)
        o.sign(wallet)
        store.add_entry(o)
        
        ledger = Ledger(uidx, serial=42, base=self.parent, acl=acl, topic=ledger.topic)
        store.load()


if __name__ == '__main__':
    unittest.main()
