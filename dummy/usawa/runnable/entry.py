import argparse
import logging
import uuid
import datetime
import signal
import sys
import shutil
import getpass

from whee.valkey import ValkeyStore
from whee.fs import FsStore

import usawa.config
from usawa import Entry, Ledger, EntryPart, Asset, DemoWallet
from usawa.store import LedgerStore
from usawa.account import Account, AccountIndex, AccountType, AccountDisplay
from usawa.constant import CATEGORIES

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()



class Context:

    def __init__(self, args):
        self.cfg = usawa.config.load_config(config_dir=args.c) 
        self.state = 0
        self.commit = args.commit
    
        # entry parts
        self.description = None
        self.src = []
        self.dst = []
        self.amount = None
        self.output = None
        self.f = None
        if args.d:
            self.txdate = datetime.datetime.fromisoformat(args.d)
        else:
            self.txdate = datetime.datetime.now(datetime.UTC)
        self.attach = []

        # set up ledger
        s = args.ledger_file
        if not s:
            try:
                s = self.cfg.get('MAIN_LEDGER_FILE')
            except KeyError:
                pass
        if not s:
            raise ValueError('ledger file required')
        self.ledger = Ledger.from_file(s)
        self.fp = args.o
        self.fp_bak = None
        if self.fp == None:
            self.fp = s
            self.fp_bak = s + '_' + str(self.ledger.serial)
        self.uidx = self.ledger.uidx

        # set up accounts hierarchy, if applicable
        self.accounts = None
        s = self.cfg.get('ACCOUNTS_FILE')
        if s:
            self.accounts = AccountIndex.from_file(self.uidx, s)
        else:
            self.accounts = AccountIndex(self.uidx)
        if self.cfg.true('ACCOUNTS_STRICT'):
            self.accounts.lock()

        self.entry = Entry(-1, self.txdate, ref=args.e)
        self.db = None
        if self.cfg.get('STORE_TYPE') == 'valkey':
            dbid = self.cfg.get('VALKEY_ID')
            host = self.cfg.get('VALKEY_HOST')
            port = self.cfg.get('VALKEY_PORT')
            self.db = ValkeyStore('', host=host, port=port)
        elif self.cfg.get('STORE_TYPE') == 'fs':
            base = self.cfg.get('FSSTORE_BASE')
            self.db = FsStore(base=base, dbname='usawa')
        self.store = LedgerStore(self.db, self.ledger)
        ops = int(self.cfg.get('WALLET_OPSLIMIT', 0))
        mem = int(self.cfg.get('WALLET_MEMLIMIT', 0))
        pw = self.cfg.get('WALLET_KEY_PASSPHRASE')
        if args.p and pw == None:
            pw = getpass.getpass("passphrase: ")
        self.wallet = self.store.get_key(DemoWallet, passphrase=pw, opslimit=ops, memlimit=mem)
        self.ledger.set_wallet(self.wallet)
        if args.e:
            self.entry = self.store.get_draft(self.entry)
            self.state = 1
        else:
            self.store.put_draft(self.entry)
        self.ref = self.entry.get_ref()

        self.base = self.uidx.base
        self.k = 'src'
        self.havedst = False
        self.i = 0


    def parse_type(self, v):
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


    def parse_unit(self, v):
        return self.uidx.sym(v)


    def parse_account(self, v, typ, sym):
        account = self.accounts.check(sym, typ, v)
        if account:
            account = Account.from_path(account)
        else:
            account = self.accounts.add(v, sym=sym, typ=typ)
        return account


    def parse_amount(self, uidx, sym, v):
        return uidx.from_floatstring(sym, v)


    def parse_side(self, v):
        for k in ['src', 'dst']:
            if k.startswith(v):
                return k
        raise ValueError('invalid side: ' + v)


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


    def parse_txdate(self, v):
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
    ctx.description = input_or_default('Entry description', ctx.description)
    ctx.ref = input_or_default('External ref', ctx.ref)
    dt = datetime.datetime.utcnow()
    dt = input_or_default('Transaction date(time)', ctx.txdate)
    if isinstance(dt, str):
        dt = ctx.parse_txdate(dt)
    ctx.txdate = dt


def do_interactive_two(ctx, entry):
    r = True
    while r:
        try:
            r = enter_part(ctx, entry)
        except Exception as e:
            logg.error('err {}'.format(e))
            pass


def enter_part(ctx, entry):
        if ctx.i > 0:
            if ctx.havedst:
                ctx.k = ''
            else:
                ctx.k = 'dst'
            v = input_or_default('Entry side', ctx.k)
            if v == '':
                return False
            ctx.k = ctx.parse_side(v)
            if v == 'dst':
                ctx.havedst = True

        v = input_or_default('Entry {} unit'.format(ctx.k), ctx.base)
        unit = ctx.parse_unit(v)
        if ctx.base != unit:
            ctx.base = unit

        v = input_or_default('Entry {} type'.format(ctx.k))
        typ = ctx.parse_type(v)

        v = input_or_default('Entry {} account'.format(ctx.k))
        account = ctx.parse_account(v, sym=unit, typ=typ)

        amount = None
        v = input_or_default('Entry {} amount'.format(ctx.k), amount)
        amount = ctx.parse_amount(ctx.uidx, unit, v)

        isdebit = ctx.k=='src'
        part = EntryPart(unit, typ.value, account.to_path(display=AccountDisplay.path), amount, debit=isdebit)
        entry.add_part(part)

        ctx.i += 1

        return True

def main():
    def croak(*args, **kwargs):
        sys.exit(1)

    signal.signal(signal.SIGINT, croak)
    signal.signal(signal.SIGTERM, croak)

    argp = argparse.ArgumentParser()
    argp.add_argument('-e', type=str, help='unique reference of entry')
    argp.add_argument('-x', type=str, action='append', default=[], help='unique reference of attachment')
    argp.add_argument('-z', type=str, action='append', default=[], help='sum of attachment')
    argp.add_argument('-v', type=str, choices=['info','debug','warning','error'], help='be verbose')
    argp.add_argument('-c', type=str, help='override config dir')
    argp.add_argument('-d', type=str, help='transaction date or datetime')
    argp.add_argument('-o', type=str, help='output ledger state')
    argp.add_argument('-p', action='store_true', help='unlock wallet with password')
    argp.add_argument('--commit', action='store_true', dest='commit', help='commit to ledger')
    argp.add_argument('ledger_file', type=str, help='ledger file')
    args = argp.parse_args()

    if args.v:
        logg.setLevel(getattr(logging, args.v.upper()))

    ctx = Context(args)

    entry = None
    if ctx.state == 0:
        do_interactive_one(ctx)
        entry = Entry.empty(ref=ctx.ref, unitindex=ctx.uidx, tx_date=ctx.txdate)
        entry = ctx.store.get_draft(entry)
        entry.description = ctx.description
        entry.dt = ctx.txdate
        do_interactive_two(ctx, entry)
    else:
        entry = ctx.entry


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

    if ctx.commit:
        if entry.serial != -1:
            raise AttributeError('entry draft already marked as committed')
        entry.serial = ctx.ledger.next_serial()


    v = input_or_default('Commit? (type YES, any other input is no)', '')
    if v == 'YES':
        entry.parent = ctx.ledger.cur
        entry.sign(ctx.wallet)
        entry.serial = ctx.ledger.next_serial()
        ctx.store.add_entry(entry, update_ledger=True)
        ctx.ledger.truncate()
        ctx.ledger.sign()
        if ctx.fp_bak != None:
            shutil.copy(ctx.fp, ctx.fp_bak)
        f = open(ctx.fp, 'w')
        f.write(ctx.ledger.to_string())
        f.close()
    else:
        ctx.store.put_draft(entry)

    print(entry)


if __name__ == '__main__':
    main()
