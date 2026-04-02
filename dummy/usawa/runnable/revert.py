import argparse
import os
import uuid
import logging
import sys
import uuid

from usawa import Entry, Ledger
from usawa.store import LedgerStore
import usawa.config
from usawa.context import UsawaContext

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

QUERYTYPE_SERIAL = 1
QUERYTYPE_UUID = 2
QUERYTYPE_SHA512 = 3


def parse_entry_spec(v):
    try:
        uu = uuid.UUID(v)
        return (QUERYTYPE_UUID, str(uu),)
    except ValueError:
        pass

    try:
        r = int(v)
        return (QUERYTYPE_SERIAL, r,)
    except ValueError:
        pass

    r = bytes.fromhex(v)
    if len(r) != 64:
        raise ValueError()
    return (QUERYTYPE_SHA512, v,)


def main():
    argp = argparse.ArgumentParser()
    argp.add_argument('-c', type=str, help='override config dir')
    argp.add_argument('-p', action='store_true', help='use passphrase to open wallet')
    argp.add_argument('-v', type=str, choices=['info','debug','warning','error'], help='be verbose')
    argp.add_argument('-i', type=str, help='ledger xml file input')
    argp.add_argument('-o', type=str, help='ledger xml file output')
    argp.add_argument('entry_spec', type=str, help='uuid, serial or hash of entry to reverse')
    args = argp.parse_args()

    if args.v:
        logg.setLevel(getattr(logging, args.v.upper()))

    cfg = usawa.config.load_config(config_dir=args.c) 
    ctx = UsawaContext(cfg)
    ctx.init(args)

    r = parse_entry_spec(args.entry_spec)
    if r[0] != QUERYTYPE_SERIAL:
        raise NotImplementedError("only serial lookup implemented")

    o = Entry.empty(serial=r[1])
    v = ctx.store.get_entry(o)

    #ctx.store.load()
    ledger = Ledger(ctx.uidx, topic=ctx.ledger.topic)
    ledger.set_wallet(ctx.wallet)
    store = LedgerStore(ctx.db, ledger)
    store.load()
    o = v.clone(invert_parts=True)
    o.parent = ledger.cur
    o.ref = str(uuid.uuid4())
    o.description = 'revert: ' + v.ref + ' (' + str(v.serial) + ')'
    o.serial = ledger.serial
    o.sign(ctx.wallet)
    v = input(str(o) + "\nCommit? (YES to confirm)): ")
    if v != 'YES':
        sys.exit(0)

    store.add_entry(o, update_ledger=True)
    if ctx.resolver != None:
        ctx.resolver.put_entry(o, lookup='sha512')
    ctx.commit(ledger=ledger)


if __name__ == '__main__':
    main()
