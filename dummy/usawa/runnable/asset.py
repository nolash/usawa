import argparse
import logging
import os
import io
import sys

from whee.valkey import ValkeyStore

import usawa.config
from usawa import Asset
from usawa.context import UsawaContext
from usawa.store import AssetStore

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()


def main():
    argp = argparse.ArgumentParser()
    argp.add_argument('-x', type=str, help='unique reference of asset')
    argp.add_argument('-e', type=str, help='external reference of asset')
    argp.add_argument('-z', type=str, help='digest of asset')
    argp.add_argument('-n', type=str, help='asset filename')
    argp.add_argument('-f', type=str, help='asset file')
    argp.add_argument('--force', action='store_true', default=False, help='overwrite if exists')
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

    w = None
    if ctx.resolver:
        w = io.BytesIO()
    asset = None
    digest = None
    if args.f:
        asset = Asset.from_file(args.f, ref=args.x, extref=args.e, mimetype=args.m, slug=args.n, w=w)
        digest = asset.get_digest(binary=True)
    elif args.z:
        digest = bytes.fromhex(args.z)
        asset = Asset(digest=digest, ref=args.x, extref=args.e, mimetype=args.m, slug=args.n)
    else:
        raise ValueError('Must provide either file path or digest')

    try:
        ctx.store.add_asset(asset, overwrite=args.force)
    except FileExistsError:
        logg.error('record already exists for {}'.format(digest.hex()))
        sys.exit(1)
    if w != None:
        k = digest
        v = w.getvalue()
        ctx.resolver.put(k, v)

    print(asset.ref)


if __name__ == '__main__':
    main()
