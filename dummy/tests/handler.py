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


def zero_handler(v):
    logg.debug('zero handler arg 0x{}'.format(v.hex()))
    return 0


def create_handler():
    handler = Handler()
    handler.register(0, zero_handler)
    return handler


class TestHandler(unittest.TestCase):
    
    def setUp(self):
        self.store = MemStore()


    def test_handler(self):
        handler = create_handler()
        b = b'\x00\x00\x00\x00'
        r = handler.scan(b)
        self.assertEqual(r, 0)


    def test_handler_pair_invalid(self):
        handler = create_handler()
        b = b'\x00\x00\x00\x00\x09\x00\x00\x00'
        r = handler.scan(b)
        self.assertEqual(r, 0)
        with self.assertRaises(ValueError):
            handler.scan(b'')

    
    def test_handler_twopass(self):
        handler = create_handler()
        b = b'\x00\x00\x00'
        r = handler.scan(b)
        self.assertEqual(r, 1)
        b = b'\x00'
        r = handler.scan(b)
        self.assertEqual(r, 0)


    def test_handler_twopass_pair(self):
        handler = create_handler()
        b = b'\x00\x00\x00\x00\x09\x00\x00'
        r = handler.scan(b)
        self.assertEqual(r, 0)
        b = b'\x00'
        r = handler.scan(b'')
        self.assertEqual(r, 1)
        with self.assertRaises(ValueError):
            handler.scan(b'\x00')


    def test_handler_twopass_pair(self):
        handler = create_handler()
        b = b'\x00\x00\x00\x00\x09\x00\x00'
        r = handler.scan(b)
        self.assertEqual(r, 0)
        b = b'\x00'
        r = handler.scan(b'')
        self.assertEqual(r, 1)
        with self.assertRaises(ValueError):
            handler.scan(b'\x00')


if __name__ == '__main__':
    unittest.main()
