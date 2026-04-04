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

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()


def try_entry_uuid(ctx, v):
    v = uuid.UUID(v)
    entry = Entry.empty(ref=str(v))
    return ctx.store.get_draft(entry)


def try_entry_serial(ctx, v):
    v = int(v)
    entry = Entry(v, None)
    return ctx.store.get_entry(entry)


def try_entry_digest(ctx, k):
    if isinstance(k, str):
        k = bytes.fromhex(k)
    if len(k) != 64:
        raise ValueError('invalid digest length')
    v = ctx.resolver.get(k)
    return Entry.from_string(v, ctx.uidx)


def try_entry(ctx, args):
    if not args.entry:
        return Entry.empty(unitindex=ctx.uidx)

    try:
        return try_entry_uuid(ctx, args.entry)
    except ValueError:
        pass

    try:
        return try_entry_serial(ctx, args.entry)
    except ValueError:
        pass

    try:
        return try_entry_digest(ctx, args.entry)
    except ValueError:
        pass

    return None


#class Context:
#
#    def __init__(self, args):
#        self.cfg = usawa.config.load_config(config_dir=args.c) 
#        self.state = 0
#        self.commit = args.commit
#    
#        # entry parts
#        self.description = None
#        self.src = []
#        self.dst = []
#        self.amount = None
#        self.output = None
#        self.f = None
#        if args.t:
#            self.txdate = datetime.datetime.fromisoformat(args.t)
#        else:
#            self.txdate = datetime.datetime.now(datetime.UTC)
#        self.attach = []
#
#        # set up ledger
#        s = args.ledger_file
#        if not s:
#            try:
#                s = self.cfg.get('MAIN_LEDGER_FILE')
#            except KeyError:
#                pass
#        if not s:
#            raise ValueError('ledger file required')
#        self.ledger = Ledger.from_file(s)
#        self.fp = args.o
#        self.fp_bak = None
#        if self.fp == None:
#            self.fp = s
#            self.fp_bak = s + '_' + str(self.ledger.serial)
#        self.uidx = self.ledger.uidx
#
#        # set up accounts hierarchy, if applicable
#        self.accounts = None
#        s = self.cfg.get('ACCOUNTS_FILE')
#        if s:
#            self.accounts = AccountIndex.from_file(self.uidx, s)
#        else:
#            self.accounts = AccountIndex(self.uidx)
#        if self.cfg.true('ACCOUNTS_STRICT'):
#            self.accounts.lock()
#
#        self.entry = Entry(-1, self.txdate, ref=args.e)
#        self.db = None
#        if self.cfg.get('STORE_TYPE') == 'valkey':
#            dbid = self.cfg.get('VALKEY_ID')
#            host = self.cfg.get('VALKEY_HOST')
#            port = self.cfg.get('VALKEY_PORT')
#            self.db = ValkeyStore('', host=host, port=port)
#        elif self.cfg.get('STORE_TYPE') == 'fs':
#            base = self.cfg.get('FSSTORE_BASE')
#            self.db = FsStore(base=base, dbname='usawa')
#        self.store = LedgerStore(self.db, self.ledger)
#        ops = int(self.cfg.get('WALLET_OPSLIMIT', 0))
#        mem = int(self.cfg.get('WALLET_MEMLIMIT', 0))
#        pw = self.cfg.get('WALLET_KEY_PASSPHRASE')
#        if args.p and pw == None:
#            pw = getpass.getpass("passphrase: ")
#        self.wallet = self.store.get_key(DemoWallet, passphrase=pw, opslimit=ops, memlimit=mem)
#        self.ledger.set_wallet(self.wallet)
#        if args.e:
#            self.entry = self.store.get_draft(self.entry)
#            self.state = 1
#        else:
#            self.store.put_draft(self.entry)
#        self.ref = self.entry.get_ref()
#
#        self.base = self.uidx.base
#        self.k = 'src'
#        self.havedst = False
#        self.i = 0
#        self.resolver = None
#        resolver_path = self.cfg.get('FS_RESOLVER_STORE_PATH', args.r)
#        if resolver_path != None:
#            self.resolver = FSResolver(os.path.realpath(resolver_path))
#

def parse_type(ctx, v):
    v = v.lower()
    r = None
    for k in CATEGORIES:
        if k.startswith(v):
            r = k
            logg.info("expanded input '{}' to category {}".format(v, r))
            break
    if not r:
        raise ValueError('invalid type: ' + v)
    o = getattr(AccountType, r)
    logg.debug('accounttype {}'.format(o))
    return o


def parse_unit(ctx, v):
    return ctx.uidx.sym(v)


#def parse_account(ctx, v, typ, sym):
#    account = self.accounts.check(sym, typ, v)
#    if account:
#        account = Account.from_path(account)
#    else:
#        account = self.accounts.add(v, sym=sym, typ=typ)
#    return account


def parse_amount(ctx, sym, v):
    return ctx.uidx.from_floatstring(sym, v)


def parse_side(ctx, v):
    for k in ['src', 'dst']:
        if k.startswith(v):
            return k
    raise ValueError('invalid side: ' + v)


def choose_account(ctx, include_create=False):
    r = None
    accounts_r = []
    while not r:
        a = None
        if len(accounts_r) == 0:
            a = input('enter account: ')
            if a == 'q':
                raise AbortMenu()
        elif len(accounts_r) == 1:
            r = accounts_r[0]
            break
        else:
            v = input('choose match: ')
            i = None
            if v == 'q':
                raise AbortMenu()
            try:
               i = int(v)
            except ValueError:
                logg.debug('Invalid number, going back to search')
            if i != None:
                try:
                    r = accounts_r[i]
                except IndexError:
                    logg.error('Number out of range')
                continue
        accounts_r = []
        ctx.aidx.set_filter(path=a)
        i = 0
        for a in ctx.aidx:
            accounts_r.append(a)
            print('{} {}'.format(i, a))
            i += 1
        if i == 0:
            logg.debug('no accounts found')
        ctx.aidx.reset_filter()
    return r


def add_part(self, part):
    logg.info('add part {}'.format(part))
    self.part.append(part)


def validate(self):
    if len(self.src) == 0:
        raise ValueError('no src')
    if len(self.dst) == 0:
        raise ValueError('no dst')
    if self.ref == None:
        raise ValueError('invalid ref')


def parse_txdate(ctx, v):
    return datetime.date.fromisoformat(v)


def input_or_default(prompt, default=None, postfix=': ', validate_fn=None):
    if default != None:
        postfix = ' [{}]'.format(default) + postfix
    v = input(prompt + postfix)
    if len(v) == 0:
        if default == None:
            raise ValueError('empty value and no default')
        v = default
    if validate_fn != None:
        validate_fn(v)
    return v


def do_interactive_one(ctx):
    ctx.set('havesrc', False)
    ctx.set('havedst', False)
    ctx.set('partk', 'src')
    v = input_or_default('Entry description', ctx.get('description'))
    ctx.set('description', v)
    v = input_or_default('External ref', ctx.get('ref'))
    ctx.set('ref', v)
    v = input_or_default('Transaction date(time)', ctx.get('dt'))
    if isinstance(v, str):
        v = parse_txdate(ctx, v)
    ctx.set('dt', v)


def handle_tag(ctx, entry, v):
    r = input('Tag: ')
    if v == '+':
        entry.tag(r)
    elif v == '-':
        entry.untag(r)


def handle_input(ctx, entry, v):
    if v == 'i' or v == 'o':
        k = 'src'
        if v == 'o':
            k = 'dst' 
        enter_part(ctx, entry, side=k)
        return True
    if v == 'q':
        raise StopIteration()
    if v == '+' or v == '-':
        r = handle_tag(ctx, entry, v)
        return True
    if v == 'w':
        ctx.set('commit', True)
        return False
    if v == 't':
        return False
    logg.error('invalid input')
    return True


def do_interactive_two(ctx, entry):
    r = True
    while r:
#        try:
#        r = enter_part(ctx, entry)
#        except Exception as e:
#            logg.error('err {}'.format(e))
#            pass
        v = input("> ")
        r = handle_input(ctx, entry, v)


def enter_part(ctx, entry, side=None):
    if side != None:
        ctx.set('partk', side)
    elif len(entry.debit) > 0:
        if ctx.get('havedst'):
            ctx.set('partk', 'dst')
        else:
            ctx.set('partk', 'src')
        v = input_or_default('Entry side', ctx.get('partk'))
        if v == '':
            return False
        k = parse_side(ctx, v)
        ctx.set('partk', k)

    #v = input_or_default('Entry {} account'.format(ctx.get('partk')))
    #account = parse_account(ctx, v, sym=unit, typ=typ)
    v = choose_account(ctx)
    account = Account.from_path(v)

    #amount = None
    k = ctx.get('partk')
    v = input_or_default('Account {} amount'.format(account))
    amount = parse_amount(ctx, account.sym, v)

    isdebit = k=='src'
    part = EntryPart(account.sym, account.typ.value.lower(), account.to_path(display=AccountDisplay.path), amount, debit=isdebit)
    logg.debug('addpart {}'.format(part))
    entry.add_part(part)

    if ctx.get('partk') == 'src':
        ctx.set('havesrc', True)

    if ctx.get('partk') == 'dst':
        ctx.set('havedst', True)

    return True


def do_prepare(ctx, entry=None):
    uu = uuid.uuid4()
    ctx.set('ref', str(uu))
    dt = datetime.datetime.now(datetime.UTC)
    ctx.set('dt', dt)


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

    entry = try_entry(ctx, args)
    if entry.serial > 0:
        raise NotImplementedError('entry edit not yet implemented')
    do_prepare(ctx, entry=entry)
#    entry = Entry.empty(ref=ctx.get('ref'), unitindex=ctx.uidx, tx_date=ctx.get('dt'))
    #entry = ctx.store.get_draft(entry)
    #entry.description = ctx.get('description')
    #entry.dt = ctx.txdate

    for v in args.x:
        k = uuid.UUID(v) 
        asset = Asset(ref=str(k))
        asset = ctx.store.get_asset_indexed(asset)
        entry.attach(asset)
    for v in args.z:
        k = bytes.fromhex(v)
        asset = Asset(digest=k)
        asset = ctx.store.get_asset(asset)
        entry.attach(asset)

    do_interactive_one(ctx)
    try:
        do_interactive_two(ctx, entry)
    except StopIteration:
        sys.exit(0)

#    if ctx.commit:
#        if entry.serial != -1:
#            raise AttributeError('entry draft already marked as committed')
#        entry.serial = ctx.ledger.next_serial()

#    v = input_or_default('Commit? (type YES, any other input is no)', '')
    if ctx.get('commit'):
        entry.parent = ctx.ledger.cur
        entry.serial = ctx.ledger.next_serial()
        entry.sign(ctx.wallet)
        ctx.store.add_entry(entry, update_ledger=True)
        ctx.ledger.truncate()
        ctx.ledger.sign()
#        if ctx.fp_bak != None:
#            shutil.copy(ctx.fp, ctx.fp_bak)
        f = open(ctx.ledger_path_out, 'w')
        f.write(ctx.ledger.to_string())
        f.close()
        if ctx.resolver != None:
            ctx.resolver.put_entry(entry, lookup='sha512')
    else:
        ctx.store.put_draft(entry)

    print(entry)


if __name__ == '__main__':
    main()
