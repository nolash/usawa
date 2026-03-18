import logging
import unittest
import os

from usawa import DemoWallet
from usawa.error import VerifyError

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.realpath(os.path.dirname(__file__))

class TestWallet(unittest.TestCase):

    def test_wallet_create(self):
        wallet = DemoWallet()
        v = b'foo'
        r = wallet.sign(v)
        wallet.verify(v, r)


    def test_wallet_verify(self):
        wallet = DemoWallet()
        v = b'foo'
        r = wallet.sign(v)

        k = wallet.pubkey()
        wallet = DemoWallet(publickey=k)
        wallet.verify(v, r)


    def test_wallet_export(self):
        wallet = DemoWallet()
        v = b'foo'
        r = wallet.sign(v)

        b = wallet.export()
        with self.assertRaises(VerifyError):
            wallet = DemoWallet.from_export(b, passphrase='baz')
        wallet = DemoWallet.from_export(b)
        wallet.verify(v, r)

        b = wallet.export(passphrase='bar')
        with self.assertRaises(VerifyError):
            wallet = DemoWallet.from_export(b, passphrase='baz')
        wallet = DemoWallet.from_export(b, passphrase='bar')
        wallet.verify(v, r)


if __name__ == '__main__':
    unittest.main()
