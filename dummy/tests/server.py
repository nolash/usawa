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
from usawa.store import LedgerStore
from usawa.service import Handler, UnixServer

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.realpath(os.path.dirname(__file__))


def zero_handler(v):
    logg.debug('zero handler arg 0x{}'.format(v.hex()))
    return 0


def create_handler():
    handler = Handler()
    handler.register(0, zero_handler)
    return handler


class TestSocket(unittest.TestCase):
    
    def setUp(self):
        self.uidx = UnitIndex('FOO')
        self.uidx.add('USD')
        self.store = MemStore()
        self.wallet = DemoWallet()
        self.acl = ACL.from_wallet(self.wallet)
        self.ledger = Ledger(self.uidx, acl=self.acl)
        self.workdir = tempfile.mkdtemp()


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
        srv.stop()
        th.join()


if __name__ == '__main__':
    unittest.main()
