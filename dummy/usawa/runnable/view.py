import os
import sys
import logging
import urllib.parse
import argparse
import uuid
import datetime

from usawa import Ledger, Entry, EntryPart, DemoWallet, UnitIndex, load
from usawa.constant import CATEGORIES
from usawa.store import LedgerStore
from whee.valkey import ValkeyStore

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()


class Context:

    def __init__(self):
        self.unit = None
        self.uidx = None


argp = argparse.ArgumentParser()
argp.add_argument('ledger_xml_file', type=str, help='load ledger metadata from XML file')
arg = argp.parse_args()

ledger = None
ledger_tree = load(arg.ledger_xml_file)
uidx = UnitIndex.from_tree(ledger_tree)
ledger = Ledger.from_tree(ledger_tree, uidx)

db = ValkeyStore('')
store = LedgerStore(db, ledger)
pk = store.get_key()
wallet = DemoWallet(privatekey=pk)
store.load()
