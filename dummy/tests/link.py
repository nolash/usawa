import logging
import datetime
import unittest
import os

from usawa import Entry, Ledger, UnitIndex
from usawa.link import EntryLink

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.realpath(os.path.dirname(__file__))

class TestLink(unittest.TestCase):
 
    def setUp(self):
        uidx = UnitIndex()
        ledger = Ledger(uidx)
        self.linker = EntryLink(ledger)


    def test_register(self):
        o = Entry(serial=42, tx_date=datetime.datetime.now(datetime.UTC))
        self.linker.link(o)
        o = Entry(serial=666, tx_date=datetime.datetime.now(datetime.UTC))
        self.linker.link(o)
        o = Entry(serial=42, tx_date=datetime.datetime.now(datetime.UTC))
        with self.assertRaises(FileExistsError):
            self.linker.link(o)


if __name__ == '__main__':
    unittest.main()
