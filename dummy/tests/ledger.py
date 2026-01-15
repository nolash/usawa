import logging
import datetime
import unittest
import os
import copy

import lxml.etree
from whee.mem import MemStore

from usawa import Ledger, UnitIndex, EntryPart, Entry, DemoWallet, ACL
from usawa.store import LedgerStore

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.realpath(os.path.dirname(__file__))


class TestLedger(unittest.TestCase):
    
    def setUp(self):
        self.store = MemStore()


    def test_ledger_create(self):
        uidx = UnitIndex('FOO')
        o = Ledger(uidx)
        store = LedgerStore(self.store, ledger=o)
        store.start()
        print(o.to_string())


    def test_ledger_xml(self):
        uidx = UnitIndex('USD')
    
        xml_file = os.path.join(testdir, 'test.xml')
        tree = lxml.etree.parse(xml_file)
        ledger = Ledger.from_tree(tree, uidx)


    def test_ledger_firstfew(self):
        s = 'FOO'
        uidx = UnitIndex(s)
        uidx.add('USD')
        o = Ledger(uidx)
        store = LedgerStore(self.store, ledger=o)
        store.start()
        print(o.to_string())

        wallet = DemoWallet()
        x = EntryPart('income', 'foo', 1337, src=True)
        y = EntryPart('asset', 'foo', 1337)
        v = Entry(x, y, s, o.peek(), datetime.datetime.now(), parent=o.current())
        v.sign(wallet)
        o.add_entry(v)

        x = EntryPart('expense', 'bar̈́', 42, src=True)
        y = EntryPart('liability', 'bar', 42)
        v = Entry(x, y, s, o.peek(), datetime.datetime.now(), parent=o.current())
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


if __name__ == '__main__':
    unittest.main()
