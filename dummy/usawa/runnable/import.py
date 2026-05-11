import os
import sys
import logging
import urllib.parse
import argparse
import uuid
import datetime

import usawa.config
from usawa.context import UsawaContext
from usawa import Ledger, Entry, EntryPart, DemoWallet, load, ACL
from usawa.constant import CATEGORIES
from usawa.store import LedgerStore
from whee.valkey import ValkeyStore

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()


def main():
    argp = argparse.ArgumentParser()
    argp.add_argument('-v', type=str, choices=['info','debug','warning','error'], help='be verbose')
    argp.add_argument('-c', type=str, help='override config dir')
    argp.add_argument('-i', type=str, help='input ledger state')
    argp.add_argument('-p', action='store_true', help='unlock wallet with password')
    args = argp.parse_args()

    if args.v:
        logg.setLevel(getattr(logging, args.v.upper()))

    cfg = usawa.config.load_config(config_dir=args.c) 
    ctx = UsawaContext(cfg)
    ctx.init(args)
    
    def store_entry(entry):
        ctx.store.add_entry(entry)
        logg.debug('store entry {}'.format(entry))
        for v in entry.attachment:
            ctx.store.add_asset(v, overwrite=True)

    ctx.resolver.restore_ledger(ctx.ledger, entry_callback=store_entry)

        
if __name__ == '__main__':
    main()
