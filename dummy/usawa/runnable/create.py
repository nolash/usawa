import os
import logging
import urllib.parse

from usawa import Ledger, DemoWallet, UnitIndex
from usawa.store import LedgerStore
from whee.valkey import ValkeyStore

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()


def parse_topic(v):
    topic = None
    if len(v) > 2:
        if v[:2] == '0x':
            v = v[2:]
    try:
        bytes.fromhex(v)
        topic = v
    except ValueError:
        if not isinstance(v, str):
            raise ValueError('invalid topic')
        topic = v.encode('utf-8').hex()

    return topic


def parse_unit(v):
    if not isinstance(v, str):
        raise ValueError('invalid unit string')
    return v.upper()


 
print("Creating new ledger")
v = input("Topic: ")
topic = None
if len(v) > 0:
    r = parse_topic(v)
    topic = bytes.fromhex(r)
logg.debug('topic {} -> {}'.format(v, topic))

v = input("Default unit: (default: BTC): ")
if len(v) == 0:
    v = 'BTC'
unit = parse_unit(v)

v = input("Unit decimals (default: 2): ")
if len(v) == 0:
    v = 2
dec = int(v)

uidx = UnitIndex(unit, precision=dec)

v = input("Source URI: ")
src = None
if len(v) > 0:
    o = urllib.parse.urlparse(v)
    src = urllib.parse.urlunparse(o)

v = input("XML output filename (default: start.xml):")
fp = None
if len(v) == 0:
    fp = os.path.join('.', 'start.xml')
fp = os.path.realpath(fp)


ledger = Ledger(uidx, topic=topic, src=src)


db = ValkeyStore('')
store = LedgerStore(db, ledger)
pk = None
wallet = None
try:
    pk = store.get_key()
except FileNotFoundError:
    logg.info('no default key found')
    wallet = DemoWallet()
    store.add_key(wallet)
if wallet == None:
    wallet = DemoWallet(privatekey=pk)
    logg.info('loaded existing key. {}'.format(wallet.pubkey().hex()))

logg.info('writing XML to file: {}'.format(fp))
f = open(fp, 'wb')
f.write(ledger.to_string())
f.close()
