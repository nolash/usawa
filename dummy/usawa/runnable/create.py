import os
import sys
import logging
import urllib.parse
import argparse
import datetime
import uuid

from usawa import Ledger, DemoWallet, UnitIndex, ACL
import usawa.config
from usawa.store import LedgerStore
from whee.valkey import ValkeyStore
from whee.fs import FsStore
from xdg_base_dirs import xdg_data_home

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()


class Context:

    def __init__(self):
        #self.unit = None
        #self.unit_precision = None
        self.uidx = None
        self.topic = None
        self.uri = None
        self.output = None
        self.f = None


    def close(self):
        if self.f and self.f != sys.stdout:
            self.f.close()


    def open(self, output):
        if output == '<stdout>':
            self.f = sys.stdout
            logg.debug('output is stdout')
        else:
            self.f = open(output, 'w')
        return self


    @staticmethod
    def from_args(args):
        ctx = Context()
        unitspec = None
        unit = None
        unit_precision = None
        try:
            unitspec = args.unit[0].split(':')
            unit = unitspec[0]
            logg.debug('have unit {}'.format(unit))
            unit_precision = None
            try:
                unit_precision = unitspec[1]
            except IndexError:
                unit_precision = UnitIndex.default_precision
        except IndexError:
            unit = UnitIndex.default_unit 
            unit_precision = UnitIndex.default_precision
        ctx.uidx = UnitIndex(unit, precision=unit_precision)
        for v in args.unit[1:]:
            unitspec = v.split(':')
            unit = unitspec[0]
            unit_precision = None
            try:
                unit_precision = unitspec[1]
            except IndexError:
                unit_precision = UnitIndex.default_precision
            ctx.uidx.add(unit, precision=unit_precision)

        ctx.topic = args.topic
        if ctx.topic == None:
            ctx.topic = str(uuid.uuid4())
        ctx.uri = args.src_uri
        if args.output != None:
            ctx.output = os.path.realpath(args.output)
        else:
            ctx.output = '<stdout>'
        return ctx

    
    def validate(self):
        self.topic = parse_topic(self.topic)
        self.uri = parse_uri(self.uri)
        #self.unit = parse_unit(self.unit)
        #self.unit_precision = parse_unit_precision(self.unit_precision)
        return self


def parse_topic(v):
    topic = None
    if len(v) > 2:
        if v[:2] == '0x':
            v = v[2:]
            topic = bytes.fromhex(v)
    elif isinstance(v, str):
        topic = v.encode('utf-8').hex().encode('utf-8')
    else:
        raise ValueError('invalid topic')
    return topic


def parse_unit(v):
    if not isinstance(v, str):
        raise ValueError('invalid unit string')
    return v.upper()


def parse_uri(v):
    o = urllib.parse.urlparse(v)
    return urllib.parse.urlunparse(o)


def parse_unit_precision(v):
    return int(v)


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
argp.add_argument('-t', dest='topic', type=str, help='ledger topic')
argp.add_argument('-u', '--unit', type=str, action='append', default=[], help='Units to use for transaction')
argp.add_argument('-o', type=str, dest='output', help='output file for updated XML document')
argp.add_argument('-l', type=str, dest='src_uri', help='URI for data source')
argp.add_argument('-c', type=str, help='override config dir')
arg = argp.parse_args()
ctx = Context.from_args(arg)
cfg = usawa.config.load_config(config_dir=arg.c)


def do_interactive(ctx):
    logg.debug("Creating new ledger")
    v = input_or_default("Topic", ctx.topic)

    ctx.unit = input_or_default("Default unit", ctx.unit)
    ctx.unit_precision = input_or_default("Unit decimals", ctx.unit_precision)
    ctx.uri = input_or_default("Source URI", ctx.uri)

    input_or_default("XML output filename", ctx.output)
    return ctx


if arg.i:
    ctx = do_interactive(ctx)
ctx = ctx.open(ctx.output)
ctx.validate()

ledger = Ledger(ctx.uidx, topic=ctx.topic, src=ctx.uri)
store_type = cfg.get('STORE_TYPE')
db = None
if store_type == 'valkey':
        db = ValkeyStore(
            "",
            host=cfg.get("VALKEY_HOST"),
            port=cfg.get("VALKEY_PORT"),
        )
elif store_type == 'fs':
    db = FsStore(
        base=cfg.get('FSSTORE_BASE', xdg_data_home()),
        dbname='usawa',
        )
else:
    raise ValueError('invalid store type: ' + store_type)
store = LedgerStore(db, ledger)
pk = None
wallet = None
dt = datetime.datetime.now()

cfg = usawa.config.load_config(config_dir=arg.c)

ops = int(cfg.get('WALLET_OPSLIMIT', 0))
mem = int(cfg.get('WALLET_MEMLIMIT', 0))
try:
    #pk = store.get_key()
    wallet = store.get_key(DemoWallet, passphrase=cfg.get('WALLET_KEY_PASSPHRASE'), opslimit=ops, memlimit=mem)
except FileNotFoundError:
    logg.info('no default key found')
    wallet = DemoWallet()
    store.add_key(wallet, passphrase=cfg.get('WALLET_KEY_PASSPHRASE'))
if wallet == None:
    wallet = DemoWallet(privatekey=pk)
    logg.info('loaded existing key. {}'.format(wallet.pubkey().hex()))

acl = ACL.from_wallet(wallet)
#ledger.reset(topic=ctx.topic, src=ctx.uri, acl=acl, wallet=wallet)
ledger = Ledger(ctx.uidx, topic=ctx.topic, src=ctx.uri, acl=acl, wallet=wallet)
ledger.sign()
ctx.f.write(ledger.to_string())
ctx.close()
