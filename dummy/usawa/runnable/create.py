import logging
import urllib.parse

from usawa import Ledger, DemoWallet, UnitIndex

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

v = input("Default unit: (default: BTC)")
if len(v) == 0:
    v = 'BTC'
unit = parse_unit(v)

v = input("Unit decimals (default: 2):")
if len(v) == 0:
    v = 2
dec = int(v)

uidx = UnitIndex(unit, precision=dec)

v = input("Source URI:")
src = None
if len(v) > 0:
    o = urllib.parse.urlparse(v)
    src = urllib.parse.urlunparse(o)

ledger = Ledger(uidx, topic=topic, src=src)
print(ledger.to_string())
