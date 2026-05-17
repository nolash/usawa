import logging
import datetime
import unittest
import os
import uuid

from usawa import Entry, Ledger, UnitIndex
from usawa.link import EntryLink

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.realpath(os.path.dirname(__file__))

class TestLink(unittest.TestCase):
 
    def setUp(self):
        uidx = UnitIndex()
        self.ledger = Ledger(uidx)
        self.linker = EntryLink(self.ledger)


    def test_dup(self):
        o = Entry(serial=42, tx_date=datetime.datetime.now(datetime.UTC))
        self.linker.link(o)
        o = Entry(serial=666, tx_date=datetime.datetime.now(datetime.UTC))
        self.linker.link(o)
        o = Entry(serial=42, tx_date=datetime.datetime.now(datetime.UTC))
        with self.assertRaises(FileExistsError):
            self.linker.link(o)


    def test_explicit(self):
        uu = uuid.uuid4()
        o = Entry(serial=42, tx_date=datetime.datetime.now(datetime.UTC), ref=str(uu))
        self.linker.link(o)
        o = Entry(serial=666, tx_date=datetime.datetime.now(datetime.UTC))
        self.linker.link(o, link_uuid=uu)
        o = Entry(serial=1337, tx_date=datetime.datetime.now(datetime.UTC))
        self.linker.link(o, link_uuid=uu)
        r =  self.linker.get_for(o)
        self.assertEqual(len(r), 2)
        self.assertEqual(r[0], 42)
        self.assertEqual(r[1], 666)
        r =  self.linker.get(o)
        self.assertEqual(r, str(uu))


    def test_implicit(self):
        uu = uuid.uuid4()
        entry_a = Entry(serial=42, tx_date=datetime.datetime.now(datetime.UTC), ref=str(uu))
        entry_b = Entry(serial=666, tx_date=datetime.datetime.now(datetime.UTC))
        self.linker.link_to(entry_a, entry_b)
        r =  self.linker.get_for(entry_a)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0], 666)
        r =  self.linker.get_for(entry_b)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0], 42)


    def test_implicit_ref(self):
        linker = EntryLink(self.ledger, refs=True)
        uu = uuid.uuid4()
        entry_a = Entry(serial=42, tx_date=datetime.datetime.now(datetime.UTC), ref=str(uu))
        entry_b = Entry(serial=666, tx_date=datetime.datetime.now(datetime.UTC))
        linker.link_to(entry_a, entry_b)
        o = Entry(serial=0, tx_date=datetime.datetime.now(datetime.UTC), ref=str(uu))
        r =  linker.get_for(o)
        self.assertEqual(len(r), 2)
        self.assertEqual(r[0], 42)
        self.assertEqual(r[1], 666)


    def test_entry_serialize(self):
        uu = uuid.uuid4()
        entry_a = Entry(serial=42, tx_date=datetime.datetime.now(datetime.UTC), ref=str(uu))
        entry_b = Entry(serial=666, tx_date=datetime.datetime.now(datetime.UTC))
        self.linker.link_to(entry_a, entry_b)
        v = entry_a.serialize(linker=self.linker)
        linker = EntryLink(self.ledger)
        o = Entry.deserialize(v, linker=linker)
        v = linker.get(o)
        self.assertEqual(v, str(uu))


if __name__ == '__main__':
    unittest.main()
