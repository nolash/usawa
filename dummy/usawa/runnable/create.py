import os
import sys
import logging
import urllib.parse
import argparse
import datetime
import uuid
import getpass

from usawa import Ledger, DemoWallet, UnitIndex, ACL
from usawa.context import UsawaContext
import usawa.config
from usawa.store import LedgerStore
from whee.valkey import ValkeyStore
from whee.fs import FsStore
from xdg_base_dirs import xdg_data_home

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()


# TODO: Move to ledger internal
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


def main():
    argp = argparse.ArgumentParser()
    argp.add_argument('-t', dest="topic", type=str, help='ledger topic')
    argp.add_argument('-v', type=str, choices=['info','debug','warning','error'], help='be verbose')
    argp.add_argument('-u', '--unit', type=str, action='append', default=[], help='Units to use for transaction')
    argp.add_argument('-p', action='store_true', help='Use passphrase to open wallet')
    argp.add_argument('-o', type=str, dest='output', help='output file for updated XML document')
    argp.add_argument('-l', type=str, dest='src_uri', help='URI for data source')
    argp.add_argument('-c', type=str, help='override config dir')
    argp.add_argument('-k', type=str, dest='pubkey', help='public key identity to use for signing')
    argp.add_argument('-y', '--with-keyring', type=str, dest='keyring', help='use keyring with given usawa identifier')
    args = argp.parse_args()

    if args.v:
        logg.setLevel(getattr(logging, args.v.upper()))

    cfg = usawa.config.load_config(config_dir=args.c, topic=args.topic)

    ctx = UsawaContext(cfg)
    ctx.init(args, create=True)
    ctx.ledger.sign()
    ctx.store.save_state()
    ctx.write(ctx.ledger.to_string())


if __name__ == '__main__':
    main()
