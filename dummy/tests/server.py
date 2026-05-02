import logging
import datetime
import unittest
import os
import copy
import tempfile
import shutil
import uuid
import threading
import time

import lxml.etree
from whee.mem import MemStore

from usawa import DemoWallet, Ledger, Entry, EntryPart, ACL, UnitIndex
from usawa.store import LedgerStore, pfx_entry
from usawa.service import Handler, UnixServer, UnixClient

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.realpath(os.path.dirname(__file__))

hash_of_foo = b'7fbba6e0636f890e56fbbf3283e524c6fa3204ae298382d624741d0dc6638326e282c41be5e4254d8820772c5518a2c5a8c0c7f7eda19594a7eb539453e1ed7'


def zero_handler(v):
    logg.debug('zero handler arg 0x{}'.format(v.hex()))
    return b'\x00'


def create_handler():
    handler = Handler()
    handler.register(0, zero_handler)
    return handler


class TestSocket(unittest.TestCase):
    
    def setUp(self):
        self.uidx = UnitIndex('FOO')
        self.uidx.add('USD')
        self.db = MemStore()
        self.wallet = DemoWallet()
        self.acl = ACL.from_wallet(self.wallet)
        self.ledger = Ledger(self.uidx, acl=self.acl, wallet=self.wallet)
        self.workdir = tempfile.mkdtemp()
        self.store = LedgerStore(self.db, self.ledger)


    def tearDown(self):
        shutil.rmtree(self.workdir)


    def serve(self, srv):
        srv.start()


    def test_disconnect(self):
        s = str(uuid.uuid4())
        srv_path = os.path.join(self.workdir, s)
        srv = UnixServer(self.store, self.ledger, path=srv_path)
        th = threading.Thread(target=self.serve, args=(srv,))
        th.start()
        client = UnixClient(path=srv_path)
        #client.get(b'\x00\x01\x02')
        client.close()
        srv.stop()
        th.join()


    def test_socket_entry_get(self):
        s = 'FOO'
        x = EntryPart(s + '.Income/foo', 1337, debit=True)
        y = EntryPart(s + '.Asset/foo', 1337)
        entry = Entry(self.ledger.peek(), datetime.datetime.now(), parent=self.ledger.current())
        entry.add_part(x)
        entry.add_part(y)
        entry.sign(self.wallet)
        self.store.add_entry(entry, update_ledger=True)

        s = str(uuid.uuid4())
        srv_path = os.path.join(self.workdir, s)
        srv = UnixServer(self.db, self.ledger, path=srv_path)
        th = threading.Thread(target=self.serve, args=(srv,))
        th.start()
        client = UnixClient(path=srv_path)

        k = pfx_entry(self.ledger, entry)
        client.get(k)
        client.close()
        srv.stop()
        th.join()


    def test_socket_entry_getnotfound(self):
        s = str(uuid.uuid4())
        srv_path = os.path.join(self.workdir, s)
        srv = UnixServer(self.db, self.ledger, path=srv_path)
        th = threading.Thread(target=self.serve, args=(srv,))
        th.start()
        client = UnixClient(path=srv_path)

        with self.assertRaises(FileNotFoundError):
            client.get(hash_of_foo)
        client.close()
        srv.stop()
        th.join()



    def test_socket_entry_putget(self):
        s = 'FOO'
        x = EntryPart(s + '.Income/foo', 1337, debit=True)
        y = EntryPart(s + '.Asset/foo', 1337)
        entry = Entry(self.ledger.peek(), datetime.datetime.now(), parent=self.ledger.current())
        entry.add_part(x)
        entry.add_part(y)

        s = str(uuid.uuid4())
        srv_path = os.path.join(self.workdir, s)
        srv = UnixServer(self.db, self.ledger, path=srv_path)
        th = threading.Thread(target=self.serve, args=(srv,))
        th.start()
        client = UnixClient(path=srv_path)

        k = pfx_entry(self.ledger, entry)
        v = entry.wrap(wallet=self.wallet)
        client.put(k, v)
        r = client.get(k)
        client.close()
        srv.stop()
        th.join()
        #Entry.unwrap(r, acl=self.acl)
        Entry.unwrap(r)


if __name__ == '__main__':
    unittest.main()
