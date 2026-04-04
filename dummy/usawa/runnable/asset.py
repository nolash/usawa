import argparse
import logging
import os

from whee.valkey import ValkeyStore

import usawa.config
from usawa import Asset
from usawa.context import UsawaContext
from usawa.store import AssetStore

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()


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

cfg = usawa.config.load_config(config_dir=args.c) 
ctx = UsawaContext(cfg, signing=False)
ctx.init(args, store_scope='asset')

asset = None
if args.f:
        asset = Asset.from_file(args.f, extref=args.e, mimetype=args.m, slug=args.n)
elif args.z:
    digest = bytes.fromhex(args.z)
    asset = Asset(digest=digest, ref=args.e, mimetype=args.m, slug=args.n)
else:
    raise ValueError('Must provide either file path or digest')

ctx.store.add_asset(asset, overwrite=True)

print(asset.ref)
