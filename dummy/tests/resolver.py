import unittest
import logging
import tempfile
import hashlib
import shutil
import os
import datetime

import lxml.etree

from usawa import Ledger, UnitIndex, Entry, EntryPart, DemoWallet
from usawa.resolve.fs import FSResolver
from usawa.error import VerifyError


logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.realpath(os.path.dirname(__file__))

hash_of_foo = 'f7fbba6e0636f890e56fbbf3283e524c6fa3204ae298382d624741d0dc6638326e282c41be5e4254d8820772c5518a2c5a8c0c7f7eda19594a7eb539453e1ed7'
hash_of_bar = 'd82c4eb5261cb9c8aa9855edd67d1bd10482f41529858d925094d173fa662aa91ff39bc5b188615273484021dfb16fd8284cf684ccf0fc795be3aa2fc1e6c181'

class TestResolver(unittest.TestCase):
    
    def setUp(self):
        self.parent = b'\x00' * 64
        self.path = tempfile.mkdtemp()
        self.backend = FSResolver(self.path) 
        self.dtreg = datetime.datetime.now()


    def tearDown(self):
        shutil.rmtree(self.path)


    def test_resolve_putget(self):
        h = hashlib.sha512()
        v = os.urandom(1337)
        h.update(v)
        k = h.digest()
        self.backend.put(k, v)
        r = self.backend.get(k)
        self.assertEqual(r, v)

        k_wrong = os.urandom(32)
        with self.assertRaises(ValueError):
            r = self.backend.get(k_wrong)

    
    def test_resolve_get_evil(self):
        fp = os.path.join(self.path, hash_of_foo)
        f = open(fp, 'wb')
        f.write(b'bar')
        f.close()
        with self.assertRaises(VerifyError):
            self.backend.get(hash_of_foo)


    def test_resolve_lookup(self):
        uidx = UnitIndex('FOO')
        wallet = DemoWallet()
        ledger = Ledger(uidx, wallet=wallet, topic=hash_of_foo.encode('utf-8'))
        dst = EntryPart('FOO', 'asset', 'foo', 1337)
        src = EntryPart('FOO', 'income', 'foo', 1337, debit=True)
        entry = Entry(42, datetime.datetime.strptime('2025-11-11', '%Y-%m-%d'), parent=self.parent, tx_datereg=self.dtreg)
        entry.add_part(src, debit=True)
        entry.add_part(dst)
        entry.sign(wallet)
        ledger.add_entry(entry)

        dst = EntryPart('FOO', 'expense', 'bar̈́', 42, debit=True)
        src = EntryPart('FOO', 'liability', 'bar', 42)
        entry = Entry(ledger.peek(), datetime.datetime.now(), parent=ledger.current())
        entry.add_part(src, debit=True)
        entry.add_part(dst)
        entry.sign(wallet)
        ledger.add_entry(entry)

        #s = lxml.etree.tostring(tree)
        ledger.truncate(lookup='sha512')
        tree = ledger.to_tree(lookup='sha512')
        s = lxml.etree.tostring(tree)
        print(s.decode('utf-8'))

        for k in ledger.entries.keys():
            tree = ledger.entries[k].to_tree()
            s = lxml.etree.tostring(tree)

        ledger.truncate() 


if __name__ == '__main__':
    unittest.main()
