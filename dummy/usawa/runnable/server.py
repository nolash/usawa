import logging
import argparse
import signal
#import threading

from usawa import Ledger, Entry, EntryPart, DemoWallet, ACL, UnitIndex, load
from usawa.context import Context
from usawa.service import Handler, UnixServer
from whee.valkey import ValkeyStore


logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

def parse(v):
    logg.debug('parsing {}'.format(v.hex()))


def main():
    argp = argparse.ArgumentParser(
            prog='usawa socket server',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description="""Provides a store agnostic middleware layer served on a socket
            
The server pairs with the usawa.service.UnixClient implementation, which can be used as the store argument for the usawa.store.LedgerStore.

It uses valkey as backend for the store, and needs a valkey service to connect to.

Loading ledger state is available from XML only.

Public keys used to verify entries and ledger states are provided using the -k flag. The server will not allow unverified items.
""",
            epilog="Currently only UNIX socket are supported",
            )
    argp.add_argument('-k', action='append', type=str, default=[], help='Add public key to list of valid signers')
    argp.add_argument('-u', type=str, default='./usawa.socket', help='UNIX Socket file to listen on')
    argp.add_argument('--valkey-host', dest='valkey_host', type=str, default='localhost', help='Valkey host')
    argp.add_argument('--valkey-port', dest='valkey_port', type=int, default=6379, help='Valkey port')
    argp.add_argument('ledger_xml_file', type=str, help='load ledger metadata from XML file')
    arg = argp.parse_args()

    acl = ACL()
    for k in arg.k:
        acl.add(k)

    ledger = None
    ledger_tree = load(arg.ledger_xml_file)
    uidx = UnitIndex.from_tree(ledger_tree)
    ledger = Ledger.from_tree(ledger_tree, acl=acl)
    
    db = ValkeyStore('', host=arg.valkey_host, port=arg.valkey_port)
    #srv = TCPServer(db, ledger, acl=acl)
    srv = UnixServer(db, ledger, acl=acl, path=arg.u)

    def stop_server(sig, stack):
        srv.stop()

    signal.signal(signal.SIGINT, stop_server)
    signal.signal(signal.SIGTERM, stop_server)
    srv.start()
    logg.debug('stopping')

if __name__ == '__main__':
    main()
