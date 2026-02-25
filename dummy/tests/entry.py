import logging
import datetime
import unittest
import os

from usawa import EntryPart, Entry, DemoWallet, ACL, UnitIndex, Asset
from usawa.error import ACLError
import lxml.etree

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.realpath(os.path.dirname(__file__))

class TestEntry(unittest.TestCase):
    
    def setUp(self):
        self.parent = bytes.fromhex('0cf9180a764aba863a67b6d72f0918bc131c6772642cb2dce5a34f0a702f9470ddc2bf125c12198b1995c233c34b4afd346c54a2334c350a948a51b6e8b4e6b6')
        self.ref = '1bda7dfa-b8fd-400d-8b42-1d2861ad7f70'
        self.description = "foo bar baz"
        self.dtreg = datetime.datetime.now()
        self.uidx = UnitIndex('FOO')


    def test_entry_serialize(self):
        dst = EntryPart('FOO', 'asset', 'foo', 1337)
        src = EntryPart('FOO', 'income', 'foo', 1337, debit=True)
        o = Entry(42, datetime.datetime.strptime('2025-11-11', '%Y-%m-%d'), parent=self.parent, ref=self.ref, description=self.description, tx_datereg=self.dtreg)
        o.add_part(src, debit=True)
        o.add_part(dst)

        s = o.serialize()
        o = Entry.deserialize(s)
        ss = o.serialize()

        self.assertEqual(s, ss)


    def test_wallet_create(self):
        pk = bytes.fromhex('b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c')
        o = DemoWallet()
        o = DemoWallet(privatekey=pk)
        pubk = o.pubkey()
        oo = DemoWallet(publickey=pubk)
        self.assertEqual(o.pubkey(), oo.pubkey())


    def test_entry_sign_verify(self):
        dst = EntryPart('FOO', 'asset', 'foo', 1337)
        src = EntryPart('FOO', 'income', 'foo', 1337, debit=True)
        o = Entry(42, datetime.datetime.strptime('2025-11-11', '%Y-%m-%d'), parent=self.parent, ref=self.ref, description=self.description, tx_datereg=self.dtreg)
        o.add_part(src, debit=True)
        o.add_part(dst)
        wallet = DemoWallet()
        data = o.wrap(wallet=wallet)
        r = Entry.unwrap(data)


    def test_entry_sign_verify_imported(self):
        dst = EntryPart('FOO', 'asset', 'foo', 1337)
        src = EntryPart('FOO', 'income', 'foo', 1337, debit=True)
        o = Entry(42, datetime.datetime.strptime('2025-11-11', '%Y-%m-%d'), parent=self.parent, ref=self.ref, description=self.description, tx_datereg=self.dtreg)
        o.add_part(src, debit=True)
        o.add_part(dst)
        wallet = DemoWallet()
        (digest, sig, msg) = o.sign(wallet)
        tree = o.to_tree()
        s = lxml.etree.tostring(tree, method='c14n2')
        logg.debug('string {}'.format(s))
        
        tree = lxml.etree.fromstring(s)
        o = Entry.from_tree(tree, self.uidx)
        o.verify(wallet)


    def test_entry_acl_verify(self):
        dst = EntryPart('FOO', 'asset', 'foo', 1337)
        src = EntryPart('FOO', 'income', 'foo', 1337, debit=True)
        o = Entry(42, datetime.datetime.strptime('2025-11-11', '%Y-%m-%d'), parent=self.parent, ref=self.ref, description=self.description, tx_datereg=self.dtreg)
        o.add_part(src, debit=True)
        o.add_part(dst)
        wallet = DemoWallet()
        data = o.wrap(wallet)
        pubk_wrong = bytes.fromhex('72f25d90ef4cfecda8fa2c47561af5af0a10a92bfd15986b1f916358bf6ac8a37858a14d27329506a3766bad0f34d2e04caf397c1607b4380eb33c97d37dfc37')
        acl = ACL()
        with self.assertRaises(ACLError):
            Entry.unwrap(data, acl=acl)
        acl.add(pubk_wrong, label='wrong')
        with self.assertRaises(ACLError):
            Entry.unwrap(data, acl=acl)
        acl.add(wallet.pubkey(), label='right')
        Entry.unwrap(data, acl=acl)


    def test_entry_export_import(self):
        dst = EntryPart('FOO', 'asset', 'foo', 1337)
        src = EntryPart('FOO', 'income', 'foo', 1337, debit=True)
        o = Entry(42, datetime.datetime.strptime('2025-11-11', '%Y-%m-%d'), parent=self.parent, ref=self.ref, description=self.description, tx_datereg=self.dtreg)
        o.add_part(src, debit=True)
        o.add_part(dst)
        wallet = DemoWallet()
        o.sign(wallet)
        tree = o.to_tree()

        s = lxml.etree.tostring(tree)
        tree = lxml.etree.fromstring(s)
        tree = Entry.from_tree(tree, self.uidx)


    def test_entry_attach(self):
        dst = EntryPart('FOO', 'asset', 'foo', 1337)
        src = EntryPart('FOO', 'income', 'foo', 1337, debit=True)
        o = Entry(42, datetime.datetime.strptime('2025-11-11', '%Y-%m-%d'), parent=self.parent, ref=self.ref, description=self.description, tx_datereg=self.dtreg)
        o.add_part(src, debit=True)
        o.add_part(dst)

        fp = os.path.join(testdir, 'test.xml')
        asset = Asset.from_file(fp)
        o.attach(asset)
        wallet = DemoWallet()
        o.sign(wallet)
        tree = o.to_tree()
     
        s = lxml.etree.tostring(tree)
        tree = lxml.etree.fromstring(s)
        entry = Entry.from_tree(tree, self.uidx)


if __name__ == '__main__':
    unittest.main()
