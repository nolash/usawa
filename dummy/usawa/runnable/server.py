import logging
import argparse
#import threading

from usawa import Ledger, Entry, EntryPart, DemoWallet, ACL, UnitIndex, load
from usawa.context import Context
from usawa.service import Handler, SocketServer
from whee.valkey import ValkeyStore


logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

READ_SIZE = 2048
LISTEN_COUNT = 5


def parse(v):
    logg.debug('parsing {}'.format(v.hex()))


def main():
    argp = argparse.ArgumentParser()
    argp.add_argument('-k', action='append', type=str, default=[], help='Add public key to list of valid signers')
    argp.add_argument('ledger_xml_file', type=str, help='load ledger metadata from XML file')
    arg = argp.parse_args()

    acl = ACL()
    for k in arg.k:
        acl.add(k)

    ledger = None
    ledger_tree = load(arg.ledger_xml_file)
    uidx = UnitIndex.from_tree(ledger_tree)
    ledger = Ledger.from_tree(ledger_tree, acl=acl)
    
    db = ValkeyStore('')
    srv = SocketServer(db, ledger, acl=acl)
    #srv.start()


if __name__ == '__main__':
    main()
