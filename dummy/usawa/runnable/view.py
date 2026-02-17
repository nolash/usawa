import os
import sys
import logging
import urllib.parse
import argparse
import uuid
import datetime

from usawa import Ledger, Entry, EntryPart, DemoWallet, UnitIndex, load, ACL
from usawa.constant import CATEGORIES
from usawa.store import LedgerStore
from whee.valkey import ValkeyStore

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()


class Context:

    def __init__(self):
        self.unit = None
        self.uidx = None
        self.output = None
        self.f = None
        self.valkey_host = None
        self.valkey_port = None


    def close(self):
        if self.f and self.f != sys.stdout:
            self.f.close()


    def open(self, output):
        if output == '<stdout>':
            self.f = sys.stdout.buffer
            logg.debug('output is stdout')
        else:
            self.f = open(output, 'wb')
        return self

    @staticmethod
    def from_args(args):
        ctx = Context()
        if args.output != None:
            ctx.output = os.path.realpath(args.output)
        else:
            ctx.output = '<stdout>'

        ctx.valkey_host = args.valkey_host
        ctx.valkey_port = args.valkey_port

        return ctx


argp = argparse.ArgumentParser()
argp.add_argument('-o', type=str, dest='output', help='output file for resulting XML document')
argp.add_argument('--valkey-host', dest='valkey_host', type=str, default='localhost', help='Valkey host')
argp.add_argument('--valkey-port', dest='valkey_port', type=int, default=6379, help='Valkey port')
argp.add_argument('ledger_xml_file', type=str, help='load ledger metadata from XML file')
arg = argp.parse_args()
ctx = Context.from_args(arg)

ledger = None
ledger_tree = load(arg.ledger_xml_file)
uidx = UnitIndex.from_tree(ledger_tree)
ledger = Ledger.from_tree(ledger_tree)

storedb = ValkeyStore('', host=ctx.valkey_host, port=ctx.valkey_port)
store = LedgerStore(storedb, ledger)
pk = store.get_key()
wallet = DemoWallet(privatekey=pk)
acl = ACL.from_wallet(wallet)
store.load(acl=acl)
sys.stdout.write(ledger.to_string())
