import argparse
import logging
import os

from whee.valkey import ValkeyStore

import usawa.config
from usawa import Asset
from usawa.store import AssetStore

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()


class Context:

    def __init__(self, args):
        self.cfg = usawa.config.load_config(config_dir=args.c) 
        self.state = 0
        self.asset = None

        if self.cfg.get('STORE_TYPE') == 'valkey':
            dbid = self.cfg.get('VALKEY_ID')
            host = self.cfg.get('VALKEY_HOST')
            port = self.cfg.get('VALKEY_PORT')
            self.db = ValkeyStore('', host=host, port=port)
        elif self.cfg.get('STORE_TYPE') == 'fs':
            base = self.cfg.get('FSSTORE_BASE')
            self.db = FsStore(base=base, dbname='usawa')
        self.store = LedgerStore(self.db, self.ledger)

        if args.f:
            self.asset = Asset.from_file(args.f, extref=args.e, mimetype=args.m, slug=args.n)
        elif args.z:
            digest = bytes.fromhex(args.z)
            self.asset = Asset(digest=digest, ref=args.e, mimetype=args.m, slug=args.n)
        else:
            raise ValueError('Must provide either file path or digest')

        self.store.add_asset(self.asset, overwrite=True)


argp = argparse.ArgumentParser()
argp.add_argument('-e', type=str, help='unique reference of asset')
argp.add_argument('-z', type=str, help='digest of asset')
argp.add_argument('-n', type=str, help='asset filename')
argp.add_argument('-f', type=str, help='asset file')
argp.add_argument('-d', type=str, help='description of asset')
argp.add_argument('-m', type=str, help='mime type of asset')
argp.add_argument('-c', type=str, help='override config dir')
argp.add_argument('-v', type=str, choices=['info','debug','warning','error'], help='be verbose')
args = argp.parse_args()

if args.v:
    logg.setLevel(getattr(logging, args.v.upper()))

ctx = Context(args)

print(ctx.asset)
