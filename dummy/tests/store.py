import logging
import datetime
import unittest
import os
import copy
import uuid

import lxml.etree
from whee.mem import MemStore

from usawa import Ledger, UnitIndex, EntryPart, Entry, DemoWallet, Asset
from usawa.store import LedgerStore, AssetStore
from usawa.crypto import ACL

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.realpath(os.path.dirname(__file__))

hash_of_foo = bytes.fromhex('f7fbba6e0636f890e56fbbf3283e524c6fa3204ae298382d624741d0dc6638326e282c41be5e4254d8820772c5518a2c5a8c0c7f7eda19594a7eb539453e1ed7')
uuid_for_foo = uuid.UUID('9ce0268e-4add-4874-9a00-322dd0157c97')


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
        o.add_part(src)
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
        o.add_part(src)
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
        o.add_part(src)
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
        o.add_part(src)
        o.add_part(dst)
        o.sign(wallet)
        store.add_entry(o)

        ledger.sign()
        store.load(acl=acl)


    @unittest.skip('import.xml must be updated to current structure')
    def test_store_import(self):
        fp = os.path.join(testdir, 'import.xml')
        ledger = Ledger.from_file(fp)
        store = LedgerStore(self.store, ledger)
        store.put_all(store_assets=True)

        # TODO: less hacky test, perhaps a ledger.rewind() to get to zero state with everything else intact?
        topic = ledger.topic
        uidx = ledger.uidx
        acl = ledger.acl
        ledger = Ledger(uidx, topic=topic, acl=acl)
        store = LedgerStore(self.store, ledger)
        store.load(acl=acl)
        # TODO: improve this test
        self.assertEqual(len(ledger.entries), 2)


    def test_store_restore(self):
        uidx = UnitIndex('FOO')
        wallet = DemoWallet()
        acl = ACL.from_wallet(wallet)
        ledger = Ledger(uidx, base=self.parent, acl=acl, wallet=wallet)
        store = LedgerStore(self.store, ledger)

        dst = EntryPart('FOO', 'asset', 'foo', 1337)
        src = EntryPart('FOO', 'income', 'foo', 1337, debit=True)
        o = Entry(ledger.next_serial(), datetime.datetime.strptime('2025-11-11', '%Y-%m-%d'), parent=self.parent, ref=self.ref, description=self.description, tx_datereg=self.dtreg, unitindex=uidx)
        o.add_part(src)
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
        o.add_part(src)
        o.add_part(dst)
        o.sign(wallet)
        store.add_entry(o)

        ledger.truncate()
        s = ledger.to_string() 
        ledger = Ledger.from_string(s)
        store = LedgerStore(self.store, ledger)
        store.restore()
       
        self.assertEqual(len(ledger.entries), 2)



    def test_store_entry_base(self):
        uidx = UnitIndex('FOO')
        ledger = Ledger(uidx, serial=42, base=self.parent)
        store = LedgerStore(self.store, ledger)
        dst = EntryPart('FOO', 'asset', 'foo', 1337)
        src = EntryPart('FOO', 'income', 'foo', 1337, debit=True)
        o = Entry(42, datetime.datetime.strptime('2025-11-11', '%Y-%m-%d'), parent=self.parent, ref=self.ref, description=self.description, tx_datereg=self.dtreg, unitindex=uidx)
        o.add_part(src)
        o.add_part(dst)
        o.add_tag('foo')
        o.add_pair('bar', 'baz')
        store.put_draft(o)
        o = store.get_draft(o)



    def test_store_asset_index(self):
        store = AssetStore(self.store)
        asset = Asset(digest=hash_of_foo, ref=str(uuid_for_foo))
        store.add_asset(asset)

        asset = Asset(digest=hash_of_foo)
        o = store.get_asset(asset)
        self.assertEqual(o.get_digest(binary=True), hash_of_foo)
        self.assertEqual(o.get_ref(binary=True), uuid_for_foo.bytes)

        asset = Asset(ref=str(uuid_for_foo))
        o = store.get_asset_indexed(asset)
        self.assertEqual(o.get_digest(binary=True), hash_of_foo)
        self.assertEqual(o.get_ref(binary=True), uuid_for_foo.bytes)


if __name__ == '__main__':
    unittest.main()
