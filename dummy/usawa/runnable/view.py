import os
import sys
import logging
import urllib.parse
import argparse
import uuid
import datetime
#import getpass

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


def main():
    argp = argparse.ArgumentParser()
    argp.add_argument('-o', type=str, dest='output', help='output file for resulting XML document')
    #argp.add_argument('-p', action='store_true', help='prompt for password to open wallet')
    argp.add_argument('-c', type=str, help='override config dir')
    argp.add_argument('-v', type=str, choices=['info','debug','warning','error'], help='be verbose')
    argp.add_argument('-i', type=str, help='input ledger state')
    argp.add_argument('--resolve', action='store_true', help='verify that hash can be resolved')
    arg = argp.parse_args()

    if arg.v:
        logg.setLevel(getattr(logging, arg.v.upper()))

    cfg = usawa.config.load_config(config_dir=arg.c) 
    ctx = UsawaContext(cfg, signing=False)
    ctx.init(arg)

    def check_resolve(entry):
        if arg.resolve:
            (digest, data) = entry.sum()
            k = digest.hex()
            logg.info('test resolve {}'.format(k))
            ctx.resolver.get(k)

    ctx.store.load(entry_callback_post=check_resolve)
    sys.stdout.write(ctx.ledger.to_string())


if __name__ == '__main__':
    main()
