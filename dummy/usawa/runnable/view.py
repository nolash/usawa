import os
import sys
import logging
import urllib.parse
import argparse
import uuid
import datetime
#import getpass

import usawa.config
from usawa import Ledger, Entry, EntryPart, DemoWallet, UnitIndex, load, ACL
from usawa.constant import CATEGORIES
from usawa.store import LedgerStore
from whee.valkey import ValkeyStore
from whee.fs import FsStore
from xdg_base_dirs import xdg_data_home

logging.basicConfig(level=logging.WARNING)
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
#argp.add_argument('-p', action='store_true', help='prompt for password to open wallet')
argp.add_argument('-c', type=str, help='override config dir')
argp.add_argument('-v', type=str, choices=['info','debug','warning','error'], help='be verbose')
argp.add_argument('--valkey-host', dest='valkey_host', type=str, default='localhost', help='Valkey host')
argp.add_argument('--valkey-port', dest='valkey_port', type=int, default=6379, help='Valkey port')
argp.add_argument('ledger_xml_file', type=str, help='load ledger metadata from XML file')
arg = argp.parse_args()

if arg.v:
    logg.setLevel(getattr(logging, arg.v.upper()))

ctx = Context.from_args(arg)

#ledger = None
#ledger_tree = load(arg.ledger_xml_file)
#uidx = UnitIndex.from_tree(ledger_tree)
#ledger = Ledger.from_tree(ledger_tree)
ledger = Ledger.from_file(arg.ledger_xml_file)

cfg = usawa.config.load_config(config_dir=arg.c)
store_type = cfg.get('STORE_TYPE')
db = None
if store_type == 'valkey':
        db = ValkeyStore(
            "",
            host=cfg.get("VALKEY_HOST"),
            port=cfg.get("VALKEY_PORT"),
        )
elif store_type == 'fs':
    db = FsStore(
        base=cfg.get('FSSTORE_BASE', xdg_data_home()),
        dbname='usawa',
        )
else:
    raise ValueError('invalid store type: ' + store_type)
store = LedgerStore(db, ledger)
#pk = store.get_key()
#wallet = DemoWallet(privatekey=pk)
#ops = int(cfg.get('WALLET_OPSLIMIT', 0))
#mem = int(cfg.get('WALLET_MEMLIMIT', 0))
#pw = cfg.get('WALLET_KEY_PASSPHRASE')
#if arg.p and pw == None:
#    pw = getpass.getpass("passphrase: ")
#logg.debug('ops {}'.format(ops))
#wallet = store.get_key(DemoWallet, passphrase=pw, opslimit=ops, memlimit=mem)
wallet = store.get_default_key(DemoWallet)
acl = ACL.from_wallet(wallet)
store.load(acl=acl)
sys.stdout.write(ledger.to_string())
