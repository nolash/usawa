import logging
import datetime
import unittest
import os
import copy

import lxml.etree
from whee.mem import MemStore

from svcontas import Ledger, UnitIndex
from svcontas.store import LedgerStore

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



if __name__ == '__main__':
    unittest.main()
