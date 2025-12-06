import logging
import datetime
import unittest
import os
import copy

from svcontas import EntryPart, Entry, DemoWallet

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.realpath(os.path.dirname(__file__))

class TestEntry(unittest.TestCase):
    
    def setUp(self):
        self.parent = bytes.fromhex('0cf9180a764aba863a67b6d72f0918bc131c6772642cb2dce5a34f0a702f9470ddc2bf125c12198b1995c233c34b4afd346c54a2334c350a948a51b6e8b4e6b6')
        self.ref = '1bda7dfa-b8fd-400d-8b42-1d2861ad7f70'
        self.description = "foo bar baz"
        self.dtreg = datetime.datetime.now()


    def test_entry_serialize(self):
        dst = EntryPart('asset', 'foo', 1337)
        src = EntryPart('income', 'foo', 1337, src=True)
        o = Entry(src, dst, 'USD', 42, datetime.datetime.strptime('2025-11-11', '%Y-%m-%d'), parent=self.parent, ref=self.ref, description=self.description, tx_datereg=self.dtreg)
        oo = copy.deepcopy(o)

        s = o.serialize()
        o = Entry.deserialize(s)
        ss = o.serialize()

        self.assertEqual(s, ss)


    def test_entry_sign_verify(self):
        dst = EntryPart('asset', 'foo', 1337)
        src = EntryPart('income', 'foo', 1337, src=True)
        o = Entry(src, dst, 'USD', 42, datetime.datetime.strptime('2025-11-11', '%Y-%m-%d'), parent=self.parent, ref=self.ref, description=self.description, tx_datereg=self.dtreg)
        wallet = DemoWallet()
        data = o.wrap(wallet)
        r = Entry.unwrap(data, wallet)
        

if __name__ == '__main__':
    unittest.main()

