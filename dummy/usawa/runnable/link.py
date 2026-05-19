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
from usawa.link import EntryLink
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
    argp.add_argument('--link-id', type=str, help='link uuid')
    argp.add_argument('entries', nargs='+', type=str, help='entries to link')
    arg = argp.parse_args()

    if arg.v:
        logg.setLevel(getattr(logging, arg.v.upper()))

    cfg = usawa.config.load_config(config_dir=arg.c) 
    ctx = UsawaContext(cfg, signing=False)
    ctx.init(arg)

    linker = EntryLink(ctx.ledger)
    #ctx.store.load(entry_callback_post, linker=linker)
    ctx.store.load(linker=linker)
   
    entries = []
    for v in arg.entries:
        o = None
        try:
            o = Entry.empty(serial=int(v))
        except ValueError:
            o = Entry.empty(ref=uuid.UUID(v))
        entry = ctx.store.get_entry(o, linker=linker)
        logg.info('entry {}'.format(entry))
        entries.append(entry)

    anchor = None
    link_id = None
    for o in entries:
        r = linker.get(o)
        if r == None:
            if anchor == None:
                anchor = o
            link_id = anchor.ref
        elif link_id == None:
            link_id = r
        elif link_id != r:
            raise AttributeError('link {} does not match link {} for entry {}'.format(r, link_id, o))
    

    for o in entries:
        try:
            linker.link(o, link_uuid=link_id)
        except FileExistsError:
            logg.debug('link {} exists for entry {}'.format(link_id, o))
            

if __name__ == '__main__':
    main()
