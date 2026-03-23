import argparse
import logging

from whee.valkey import ValkeyStore

import usawa.config
from usawa import Entry, Ledger, EntryPart
from usawa.store import EntryStore
from usawa.account import Account, AccountIndex, AccountType, AccountDisplay
from usawa.constant import CATEGORIES

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()


class Context:

    def __init__(self, args):
        self.cfg = usawa.config.load_config(config_dir=args.c) 
        self.cmd = args.cmd
        self.state = 0
    
        # entry parts
        self.description = None
        self.src = [None, None, None]
        self.dst = [None, None, None]
        self.amount = None
        self.part = []
        self.output = None
        self.f = None
        self.attach = []
      
        # set up ledger
        s = args.l
        if not s:
            try:
                s = self.cfg.get('MAIN_LEDGER_FILE')
            except KeyError:
                pass
        if not s:
            raise ValueError('ledger file required')
        self.ledger = Ledger.from_file(s)
        self.uidx = self.ledger.uidx
        self.src[2] = self.uidx.base
        self.dst[2] = self.uidx.base

        # set up accounts hierarchy, if applicable
        self.accounts = None
        s = self.cfg.get('ACCOUNTS_FILE')
        if s:
            self.accounts = AccountIndex.from_file(self.uidx, s)
        else:
            self.accounts = AccountIndex(self.uidx)
        if self.cfg.true('ACCOUNTS_STRICT'):
            self.accounts.lock()

        self.entry = Entry.empty(ref=args.r)
        self.db = None
        if self.cfg.get('STORE_TYPE') == 'valkey':
            dbid = self.cfg.get('VALKEY_ID')
            host = self.cfg.get('VALKEY_HOST')
            port = self.cfg.get('VALKEY_PORT')
            self.db = ValkeyStore('', host=host, port=port)
        self.store = EntryStore(self.db)
        if args.r:
            self.entry = self.store.get_draft(self.entry)
            self.state = 1
        else:
            self.store.put_draft(self.entry)
        self.ref = self.entry.get_ref()


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


    def add_part(self, part):
        logg.info('add part {}'.format(part))
        self.part.append(part)


    def validate(self):
        for v in self.src:
            if v == None:
                raise ValueError('invalid src')
        for v in self.dst:
            if v == None:
                raise ValueError('invalid dst')
        if self.ref == None:
            raise ValueError('invalid ref')
     


argp = argparse.ArgumentParser()
argp.add_argument('-r', type=str, help='entry unique reference')
argp.add_argument('-v', type=str, choices=['info','debug','warning','error'], help='be verbose')
argp.add_argument('-c', type=str, help='override config dir')
argp.add_argument('-l', type=str, help='ledger file')
argp.add_argument('cmd', type=str, choices=['entry', 'asset'], help='subcommand')
args = argp.parse_args()

if args.v:
    logg.setLevel(getattr(logging, args.v.upper()))

ctx = Context(args)


   

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


def do_interactive(ctx):
    v = input_or_default('Entry description', ctx.description)
    ctx.description = v

    amounts = {
            'src': None,
            'dst': None,
            }

    for k in ['src', 'dst']:
        o = vars(ctx)
        #v = input('Entry {} type: '.format(k))

        v = input_or_default('Entry {} unit'.format(k), o[k][2])
        unit = ctx.parse_unit(v)
        o[k][2] = unit

        v = input_or_default('Entry {} type'.format(k), o[k][0])
        typ = ctx.parse_type(v)
        o[k][0] = typ

        v = input_or_default('Entry {} account'.format(k), o[k][1])
        account = ctx.parse_account(v, sym=unit, typ=typ)
        o[k][1] = account

        amount = None
        if k =='dst':
            amount = amounts['src']
        v = input_or_default('Entry {} amount'.format(k), amount)
        amount = ctx.parse_amount(ctx.uidx, unit, v)
        amount *= -1
        amounts[k] = str(amount)

        part = EntryPart(unit, typ.value, account.to_path(display=AccountDisplay.path), amount, debit=k=='src')
        ctx.add_part(part)

    ctx.ref = input_or_default('External ref', ctx.ref)

    #output = input_or_default('Output file', ctx.output)
    #logg.debug('output {}'.format(output))
    #return ctx.open(output)

entry = None
if ctx.state == 0:
    do_interactive(ctx)
    ctx.validate()
    entry = Entry.empty(description=ctx.description, ref=ctx.ref, unitindex=ctx.uidx)
    entry.add_part(ctx.part[0], debit=True)
    entry.add_part(ctx.part[1])
else:
    entry = ctx.entry

ctx.store.put_draft(entry)
print(entry)
