import argparse
import logging

from whee.valkey import ValkeyStore

import usawa.config
from usawa import Entry, Ledger
from usawa.store import EntryStore
from usawa.account import AccountIndex

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()


class Context:

    def __init__(self, args):
        self.cfg = usawa.config.load_config(config_dir=args.c) 
        self.cmd = args.cmd
       
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

        # set up accounts hierarchy, if applicable
        self.accounts = None
        s = self.cfg.get('MAIN_ACCOUNTS_FILE')
        if s:
            self.accounts = AccountIndex.from_file(self.ledger.uidx, s)
        else:
            self.accounts = AccountIndex(self.ledger.uidx)

        self.entry = Entry.empty()
        self.db = None
        if self.cfg.get('STORE_TYPE') == 'valkey':
            dbid = self.cfg.get('VALKEY_ID')
            host = self.cfg.get('VALKEY_HOST')
            port = self.cfg.get('VALKEY_PORT')
            self.db = ValkeyStore('', host=host, port=port)
        self.store = EntryStore(self.db)
        if args.r:
            self.entry = self.store.get_draft(self.entry)
        else:
            self.store.put_draft(self.entry)


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
