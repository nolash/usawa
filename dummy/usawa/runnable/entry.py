import argparse
import logging
import uuid
import datetime
import signal
import sys
import shutil
import getpass
import os

from whee.valkey import ValkeyStore
from whee.fs import FsStore

import usawa.config
from usawa.context import UsawaContext
from usawa import Entry, Ledger, EntryPart, Asset, DemoWallet
from usawa.store import LedgerStore
from usawa.resolve.fs import FSResolver
from usawa.account import Account, AccountIndex, AccountType, AccountDisplay
from usawa.constant import CATEGORIES
from usawa.cli.entry import EntrySession

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()


#def parse_type(ctx, v):
#    v = v.lower()
#    r = None
#    for k in CATEGORIES:
#        if k.startswith(v):
#            r = k
#            logg.info("expanded input '{}' to category {}".format(v, r))
#            break
#    if not r:
#        raise ValueError('invalid type: ' + v)
#    o = getattr(AccountType, r)
#    logg.debug('accounttype {}'.format(o))
#    return o
#
#

def main():
    def croak(*args, **kwargs):
        sys.exit(1)

    signal.signal(signal.SIGINT, croak)
    signal.signal(signal.SIGTERM, croak)

    argp = argparse.ArgumentParser()
    argp.add_argument('-x', type=str, action='append', default=[], help='unique reference of attachment')
    argp.add_argument('-z', type=str, action='append', default=[], help='sum of attachment')
    argp.add_argument('-v', type=str, choices=['info','debug','warning','error'], help='be verbose')
    argp.add_argument('-c', type=str, help='override config dir')
    argp.add_argument('-t', type=str, help='transaction date or datetime')
    #argp.add_argument('-r', type=str, help='export resolver spec')
    argp.add_argument('-i', type=str, help='input ledger state')
    argp.add_argument('-o', type=str, help='output ledger state')
    argp.add_argument('-p', action='store_true', help='unlock wallet with password')
    argp.add_argument('--commit', action='store_true', dest='commit', help='commit to ledger')
    argp.add_argument('entry', nargs='?', type=str, help='entry to edit')
    args = argp.parse_args()

    if args.v:
        logg.setLevel(getattr(logging, args.v.upper()))

    #ctx = Context(args)

    cfg = usawa.config.load_config(config_dir=args.c) 
    ctx = UsawaContext(cfg)
    #dp = os.path.realpath(args.src_dir)
    #ctx.set('srcdir', dp)
    ctx.init(args)
    ctx.set('unitbase', ctx.uidx.base)
    ctx.set('commit', False)

#    entry = try_entry(ctx, args)
#    if entry.serial > 0:
#        raise NotImplementedError('entry edit not yet implemented')
#    do_prepare(ctx, entry=entry)
#    entry = Entry.empty(ref=ctx.get('ref'), unitindex=ctx.uidx, tx_date=ctx.get('dt'))
    #entry = ctx.store.get_draft(entry)
    #entry.description = ctx.get('description')
    #entry.dt = ctx.txdate

    o = EntrySession(ctx, args.entry)

    for v in args.x:
        o.attach_ref(v)

    for v in args.z:
        o.attach_digest(v)
        
    entry = o.start()
    
#    if ctx.commit:
#        if entry.serial != -1:
#            raise AttributeError('entry draft already marked as committed')
#        entry.serial = ctx.ledger.next_serial()

#    v = input_or_default('Commit? (type YES, any other input is no)', '')
    
    print(entry)


if __name__ == '__main__':
    main()
