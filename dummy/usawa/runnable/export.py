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
from usawa.context import UsawaContext
from usawa import Ledger, Entry, EntryPart, DemoWallet, UnitIndex, load, ACL
from usawa.constant import CATEGORIES
from usawa.store import LedgerStore
from usawa.resolve.fs import FSResolver
from usawa.error import VerifyError

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()


def main():
    argp = argparse.ArgumentParser()
    argp.add_argument('-c', type=str, help='override config dir')
    argp.add_argument('-v', type=str, choices=['info','debug','warning','error'], help='be verbose')
    argp.add_argument('-i', type=str, help='input ledger state')
    argp.add_argument('output', type=str, help='output dir for resulting XML entry documents')
    arg = argp.parse_args()

    if arg.v:
        logg.setLevel(getattr(logging, arg.v.upper()))

    cfg = usawa.config.load_config(config_dir=arg.c) 
    ctx = UsawaContext(cfg, signing=False)
    ctx.init(arg)

    ctx.store.load()
    resolve_out = FSResolver(arg.output)
    resolve_in = ctx.resolver

    for k in ctx.ledger.entries:
        o = ctx.ledger.entries[k]
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
