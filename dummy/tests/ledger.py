import logging
import datetime
import unittest
import os
import copy

import lxml.etree
from whee.mem import MemStore

from usawa import Ledger, UnitIndex, EntryPart, Entry, DemoWallet, ACL, schema_path
from usawa.ledger import CallbackType
from usawa.store import LedgerStore
from usawa.error import VerifyError

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.realpath(os.path.dirname(__file__))


def cb_no(self):
    return False


def cb_yes(self):
    return True


class TestLedger(unittest.TestCase):
    
    def setUp(self):
        self.store = MemStore()


    def test_ledger_create(self):
        uidx = UnitIndex('FOO')
        wallet = DemoWallet()
        o = Ledger(uidx, wallet=wallet)
        store = LedgerStore(self.store, ledger=o)
        store.start()
        print(o.to_string())


    def test_ledger_xml(self):
        uidx = UnitIndex('USD')
    
        xml_file = os.path.join(testdir, 'test.xml')
        tree = lxml.etree.parse(xml_file)
        with self.assertRaises(Exception):
            logg.warning("fix the signature in test.xml")
            ledger = Ledger.from_tree(tree, uidx)


    def test_ledger_firstfew(self):
        s = 'FOO'
        uidx = UnitIndex(s)
        uidx.add('USD')
        wallet = DemoWallet()
        o = Ledger(uidx, wallet=wallet)
        store = LedgerStore(self.store, ledger=o)
        store.start()
        print(o.to_string())

        x = EntryPart(s + '.Income/foo', 1337, debit=True)
        y = EntryPart(s + '.Asset/foo', 1337)
        v = Entry(o.peek(), datetime.datetime.now(), parent=o.current())
        v.add_part(x)
        v.add_part(y)
        v.sign(wallet)
        o.add_entry(v)

        x = EntryPart(s + '.Expense/bar', 42, debit=True)
        y = EntryPart(s + '.Liability/bar', 42)
        v = Entry(o.peek(), datetime.datetime.now(), parent=o.current())
        v.add_part(x)
        v.add_part(y)
        v.sign(wallet)
        o.add_entry(v)


    def test_serialize(self):
        wallet = DemoWallet()
        acl = ACL.from_wallet(wallet)

        s = 'FOO'
        uidx = UnitIndex(s)
        o = Ledger(uidx, acl=acl, wallet=wallet)
        #b = o.serialize()
        r = o.sign()


    def test_validate(self):
        s = 'FOO'
        uidx = UnitIndex(s)
        uidx.add('USD')
        o = Ledger(uidx)
        store = LedgerStore(self.store, ledger=o)
        store.start()
    
        wallet = DemoWallet()
        o.set_wallet(wallet)
        x = EntryPart(s + '.Income/foo', 1337, debit=True)
        y = EntryPart(s + '.Asset/foo', 1337)
        v = Entry(o.peek(), datetime.datetime.now(), parent=o.current())
        v.add_part(x)
        v.add_part(y)
        v.sign(wallet)
        o.add_entry(v)

        x = EntryPart(s + '.Expense/bar', 42, debit=True)
        y = EntryPart(s + '.Liability/bar', 42)
        v = Entry(o.peek(), datetime.datetime.now(), parent=o.current())
        v.add_part(x)
        v.add_part(y)
        v.sign(wallet)
        o.add_entry(v)

        o.sign()
        v = o.to_string()

        logg.debug('schema checking xml string {}'.format(v))

        f = open(schema_path, 'r')
        b = f.read()
        f.close()
        o = lxml.etree.XML(b)
        schema = lxml.etree.XMLSchema(o)
        parser = lxml.etree.XMLParser(schema=schema)
        lxml.etree.fromstring(v, parser)


    def test_ledger_truncate(self):
        s = 'FOO'
        uidx = UnitIndex(s)
        uidx.add('USD')
        ledger = Ledger(uidx)
        store = LedgerStore(self.store, ledger=ledger)
        store.start()
    
        wallet = DemoWallet()
        ledger.set_wallet(wallet)
        x = EntryPart(s + '.Income/foo', 1337, debit=True)
        y = EntryPart(s + '.Asset/foo', 1337)
        v = Entry(ledger.peek(), datetime.datetime.now(), parent=ledger.current())
        v.add_part(x)
        v.add_part(y)
        v.sign(wallet)
        ledger.add_entry(v)

        x = EntryPart(s + '.Expense/bar', 42, debit=True)
        y = EntryPart(s + '.Liability/bar', 42)
        v = Entry(ledger.peek(), datetime.datetime.now(), parent=ledger.current())
        v.add_part(x)
        v.add_part(y)
        v.sign(wallet)
        ledger.add_entry(v)
        ledger.sign()

        ledger.truncate()
        self.assertEqual(ledger.serial, 2)


    def test_ledger_callback(self):
        s = 'FOO'
        uidx = UnitIndex(s)
        uidx.add('USD')
        ledger = Ledger(uidx)
        ledger.register_callback(cb_yes)
        ledger.register_callback(cb_yes, CallbackType.PRE)
        store = LedgerStore(self.store, ledger=ledger)
        store.start()
    
        wallet = DemoWallet()
        ledger.set_wallet(wallet)
        x = EntryPart(s + '.Income/foo', 1337, debit=True)
        y = EntryPart(s + '.Asset/foo', 1337)
        v = Entry(ledger.peek(), datetime.datetime.now(), parent=ledger.current())
        v.add_part(x)
        v.add_part(y)
        v.sign(wallet)
        ledger.add_entry(v)

        ledger.register_callback(cb_no, CallbackType.POST)
        x = EntryPart(s + '.Income/foo', 1337, debit=True)
        y = EntryPart(s + '.Asset/foo', 1337)
        v = Entry(ledger.peek(), datetime.datetime.now(), parent=ledger.current())
        v.add_part(x)
        v.add_part(y)
        v.sign(wallet)
        with self.assertRaises(VerifyError):
            ledger.add_entry(v)

if __name__ == '__main__':
    unittest.main()
