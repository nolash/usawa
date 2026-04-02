import os
import sys
import logging
import urllib.parse
import argparse
import uuid
import datetime

from whee.valkey import ValkeyStore
from whee.fs import FsStore
from xdg_base_dirs import xdg_data_home

import usawa.config
from usawa import Ledger, Entry, EntryPart, DemoWallet, UnitIndex, load, ACL
from usawa.constant import CATEGORIES
from usawa.store import LedgerStore
from usawa.resolve.fs import FSResolver
from usawa.error import VerifyError

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
        if args.output == None:
            raise ValueError('invalid output dir')
        ctx.output = os.path.realpath(args.output)

        ctx.valkey_host = args.valkey_host
        ctx.valkey_port = args.valkey_port

        return ctx


def main():
    argp = argparse.ArgumentParser()
    argp.add_argument('-o', type=str, dest='output', help='output dir for resulting XML entry documents')
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
    wallet = store.get_default_key(DemoWallet)
    acl = ACL.from_wallet(wallet)
    store.load(acl=acl)
    resolve_out = FSResolver(ctx.output)
    resolve_in = None
    resolve_in_path = cfg.get('FS_RESOLVER_STORE_PATH')
    if resolve_in_path != None:
        resolve_in = FSResolver(resolve_in_path)

    for k in ledger.entries:
        o = ledger.entries[k]
        r = resolve_out.put_entry(o, lookup='sha512')
        if resolve_in != None:
            for oo in o.attachment:
                k = oo.get_digest(binary=True)
                try:
                    v = resolve_in.get(k)
                except VerifyError:
                    logg.error('attachment retrieve fail verify: {}'.format(k.hex()))
                    continue
                resolve_out.put(k, v)
                logg.info('put attachment {}'.format(k.hex()))


if __name__ == '__main__':
    main()
