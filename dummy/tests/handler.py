import logging
import datetime
import unittest
import os
import copy

import lxml.etree
from whee.mem import MemStore

from usawa.store import LedgerStore
from usawa.service import Handler

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.realpath(os.path.dirname(__file__))


class TestHandler(unittest.TestCase):
    
    def setUp(self):
        self.store = MemStore()
        self.handler = Handler()


    def test_handler(self):
        b = b'\x00\x00\x00\x00'
        r = self.handler.scan(b)
        self.assertEqual(r, 0)


if __name__ == '__main__':
    unittest.main()
