import unittest
import logging
import tempfile
import hashlib
import shutil
import os
import datetime

import lxml.etree

from usawa import Ledger, UnitIndex, Entry, EntryPart, DemoWallet, ACL
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
        ledger = Ledger(uidx, wallet=wallet, topic=bytes.fromhex(hash_of_foo))
        dst = EntryPart('FOO', 'asset', 'foo', 1337)
        src = EntryPart('FOO', 'income', 'foo', 1337, debit=True)
        entry = Entry(1, datetime.datetime.strptime('2025-11-11', '%Y-%m-%d'), parent=self.parent, tx_datereg=self.dtreg)
        entry.add_part(dst)
        entry.add_part(src, debit=True)
        entry.sign(wallet)
        first_entry_key = self.backend.put_entry(entry, 'sha512')
        ledger.add_entry(entry)

        dst = EntryPart('FOO', 'expense', 'bar̈́', 42, debit=True)
        src = EntryPart('FOO', 'liability', 'bar', 42)
        entry = Entry(ledger.peek(), datetime.datetime.now(), parent=ledger.current())
        entry.add_part(dst)
        entry.add_part(src, debit=True)
        entry.sign(wallet)
        ledger.add_entry(entry)
        last_entry_key = self.backend.put_entry(entry, 'sha512')
        ledger.sign()

        ledger.truncate(lookup='sha512')
        logg.debug('after trunc {}'.format(ledger.lookup))

        acl = ACL.from_wallet(wallet)
        s = ledger.to_string(lookup='sha512')
        logg.debug('ledgerstring {}'.format(s))
        ledger = ledger.from_string(s, acl=acl)

        self.backend.restore_ledger(ledger)

#        tree = ledger.to_tree(lookup='sha512')
#        s = lxml.etree.tostring(tree)
#        ledger = Ledger(uidx, wallet=wallet, topic=bytes.fromhex(hash_of_foo))
#
#        k = self.backend.get(first_entry_key)
#        first_entry = Entry.from_string(k, uidx)
#        ledger.add_entry(first_entry)
#
#        k = self.backend.get(last_entry_key)
#        last_entry = Entry.from_string(k, uidx)
#        ledger.add_entry(last_entry)
#        
#        tree = ledger.to_tree(lookup='sha512')
#        s_orig = lxml.etree.tostring(tree)


if __name__ == '__main__':
    unittest.main()
