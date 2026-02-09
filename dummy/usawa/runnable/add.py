import os
import sys
import logging
import urllib.parse
import argparse
import uuid
import datetime

from usawa import Ledger, Entry, EntryPart, DemoWallet, UnitIndex, load
from usawa.constant import CATEGORIES
from usawa.store import LedgerStore
from whee.valkey import ValkeyStore

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()


class Context:

    def __init__(self):
        self.unit = None
        self.uidx = None
        self.ref = None
        self.description = None
        self.src = [None, None]
        self.dst = [None, None]
        self.amount = None
        self.part = []
        self.output = None
        self.f = None


    def close(self):
        if self.f and self.f != sys.stdout:
            self.f.close()


    def open(self, output):
        if output == '<stdout>':
            self.f = sys.stdout.buffer
            logg.debug('output is stdout')
        else:
            self.f = open(output, 'wb')
        return self


    @staticmethod
    def from_args(args):
        ctx = Context()
        ctx.unit = args.unit
        ctx.uidx = UnitIndex(ctx.unit, precision=args.unit_precision)
        if args.description != None:
            ctx.description = args.description
        if args.r != None:
            ctx.ref = args.r
        else:
            ctx.ref = str(uuid.uuid4())
        ctx.src[0] = args.src_type
        ctx.src[1] = args.src_account
        ctx.dst[0] = args.dst_type
        ctx.dst[1] = args.dst_account
        if args.amount != None:
            ctx.amount = args.amount

        if args.output != None:
            ctx.output = os.path.realpath(args.output)
        else:
            ctx.output = '<stdout>'
        return ctx


    def validate(self):
        for v in self.src:
            if v == None:
                raise ValueError('invalid src')
        for v in self.dst:
            if v == None:
                raise ValueError('invalid dst')
        if self.ref == None:
            raise ValueError('invalid ref')
        

def parse_type(v):
    if v not in CATEGORIES:
        raise ValueError('invalid type: ' + v)
    return v


def parse_account(v):
    logg.warning('account parsing is noop')
    return v


def parse_amount(uidx, sym, v):
    return uidx.from_floatstring(sym, v)


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


argp = argparse.ArgumentParser()
argp.add_argument('-i', action='store_true', help='interactive edit')
argp.add_argument('-r', type=str, help='external reference')
argp.add_argument('-s', type=str, dest='src_account', default='general', help='source account')
argp.add_argument('-t', type=str, dest='dst_account', default='general', help='destination account')
argp.add_argument('-a', type=str, dest='amount', help='source and destination amount')
argp.add_argument('-o', type=str, dest='output', help='output file for updated XML document')
argp.add_argument('--src-type', dest='src_type', type=str, choices=CATEGORIES, default='expense', help='source type')
argp.add_argument('--dst-type', dest='dst_type', type=str, choices=CATEGORIES, default='asset', help='dest type')
argp.add_argument('-d', '--description', dest='description', type=str, help='interactive edit')
# TODO: read default from xml if not defined
argp.add_argument('-u', '--unit', type=str, default=UnitIndex.default_unit, help='Unit to use for transaction')
argp.add_argument('--unit-precision', dest='unit_precision', type=int, default=UnitIndex.default_precision, help='Unit precision')
argp.add_argument('--unit-rate', dest='unit_precision', type=float, default=1.0, help='Unit exchange rate')
argp.add_argument('ledger_xml_file', type=str, help='load ledger metadata from XML file')
arg = argp.parse_args()
ctx = Context.from_args(arg)

ledger = None
logg.warning('hardcoding unit index default sym, need unitindex xml parser')
logg.warning('using default sym for all entries for now')
ledger_tree = load(arg.ledger_xml_file)
uidx = UnitIndex.from_tree(ledger_tree)
ledger = Ledger.from_tree(ledger_tree)

db = ValkeyStore('')
store = LedgerStore(db, ledger)
pk = store.get_key()
wallet = DemoWallet(privatekey=pk)
ledger.set_wallet(wallet)
dt = datetime.datetime.now()


def do_interactive(ctx):
    v = input_or_default('Entry description', ctx.description)
    ctx.description = v

    amount = None
    for k in ['src', 'dst']:
        o = vars(ctx)
        #v = input('Entry {} type: '.format(k))
        v = input_or_default('Entry {} type'.format(k), o[k][0])
        o[k][0] = parse_type(v)

        v = input_or_default('Entry {} account'.format(k), o[k][1])
        o[k][1] = parse_account(v)
      
        if amount == None:
            v = input_or_default('Entry {} amount'.format(k), ctx.amount)
            amount = parse_amount(uidx, ctx.unit, v)
        amount *= -1

        ctx.part.append(EntryPart(ctx.unit, o[k][0], o[k][1], amount, debit=k=='src'))

    ctx.ref = input_or_default('External ref', ctx.ref)

    output = input_or_default('Output file', ctx.output)
    logg.debug('output {}'.format(output))
    return ctx.open(output)
    

if arg.i:
    ctx = do_interactive(ctx)

ctx.validate()
entry = Entry(ledger.next_serial(), dt, parent=ledger.current(), description=ctx.description, ref=ctx.ref, unitindex=ctx.uidx)
entry.add_part(ctx.part[0], debit=True)
entry.add_part(ctx.part[1])
entry.sign(wallet)
logg.debug('storing entry {}'.format(entry))
store.add_entry(entry)
#ledger.add_entry(entry, modify_tree=True)
ledger.add_entry(entry)
#ledger.truncate(modify_tree=True)
ledger.truncate()
ledger.sign()
ctx.f.write(ledger.to_string())
ctx.close()
