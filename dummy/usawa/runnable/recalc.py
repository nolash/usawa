import os
import sys
import logging
import urllib.parse
import argparse
import uuid
import datetime

import usawa.config
from usawa.context import UsawaContext
from usawa import Ledger, Entry, EntryPart, DemoWallet, UnitIndex, load, ACL
from usawa.constant import CATEGORIES
from usawa.store import LedgerStore
from whee.valkey import ValkeyStore
from whee.fs import FsStore
from xdg_base_dirs import xdg_data_home

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

prev = None

def main():
    argp = argparse.ArgumentParser()
    argp.add_argument('-o', type=str, dest='output', help='output ledger state')
    #argp.add_argument('-p', action='store_true', help='prompt for password to open wallet')
    argp.add_argument('-c', type=str, help='override config dir')
    argp.add_argument('-v', type=str, choices=['info','debug','warning','error'], help='be verbose')
    argp.add_argument('-i', type=str, help='input ledger state')
    argp.add_argument('-p', action='store_true', help='unlock wallet with password')
    arg = argp.parse_args()

    if arg.v:
        logg.setLevel(getattr(logging, arg.v.upper()))

    cfg = usawa.config.load_config(config_dir=arg.c) 
    ctx = UsawaContext(cfg)
    ctx.init(arg)

    def override_parent(entry):
        global prev
        digest = ctx.ledger.cur
        if prev != None:
            (k, v) = prev.get_lookup(ctx.ledger.lookup_algo)
            ctx.ledger.cur = bytes.fromhex(k)
            entry.parent = ctx.ledger.cur
        logg.info('entry parent override {}'.format(entry.parent.hex()))
        ctx.store.add_entry(entry, overwrite=True)
        ctx.ledger.serial = entry.serial
        prev = entry

    ctx.store.load(entry_callback_pre=override_parent)
    ctx.commit()

if __name__ == '__main__':
    main()
