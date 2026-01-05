import logging
import urllib.parse
import argparse
import uuid
import datetime

from usawa import Ledger, Entry, EntryPart, DemoWallet, UnitIndex, load
from usawa.store import LedgerStore
from whee.valkey import ValkeyStore

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()


def parse_type(v):
    if v not in ['expense', 'income', 'liability', 'asset']:
        raise ValueError('invalid type')
    return v


def parse_account(v):
    logg.warning('account parsing is noop')
    return v


def parse_amount(uidx, sym, v):
    return uidx.from_floatstring(sym, v)


argp = argparse.ArgumentParser()
argp.add_argument('-f', type=str, help='load ledger metadata from XML file')
argp.add_argument('--topic', type=str, help='hexadecimal topic to load')
arg = argp.parse_args()

ledger = None
unit = 'BTC'
uidx = UnitIndex(unit)
logg.warning('hardcoding unit index default sym, need unitindex xml parser')
logg.warning('using default sym for all entries for now')
if arg.f:
    ledger_tree = load(arg.f)
    ledger = Ledger.from_tree(ledger_tree, uidx)

db = ValkeyStore('')
store = LedgerStore(db, ledger)
pk = store.get_key()
wallet = DemoWallet(privatekey=pk)
dt = datetime.datetime.now()

v = input('Entry description: ')
dsc = v

pair = []
amount = None
for k in ['src', 'dst']:
    v = input('Entry {} type: '.format(k))
    typ = parse_type(v)

    v = input('Entry {} account: '.format(k))
    account = parse_account(v)
  
    if amount != None:
        amount *= -1.0
    else:
        v = input('Entry {} amount: '.format(k))
        amount = parse_amount(uidx, unit, v)

    pair.append(EntryPart(typ, account, amount))

ref = uuid.uuid4()
logg.debug('generated ref {}'.format(ref))

entry = Entry(pair[0], pair[1], unit, ledger.serial, dt, parent=ledger.current(), description=dsc, ref=str(ref))
entry.sign(wallet)
ledger.add_entry(entry)
