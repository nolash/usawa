import argparse
import datetime

import lxml.etree
import confini
import nacl.signing

from svcontas import Ledger, Entry, DemoWallet, State, get_units, init_ledger


seed = bytes.fromhex('2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae')

state_serial = 0
state_digest = b'00' * 64



if __name__ == '__main__':
    now = datetime.datetime.now()
    argp = argparse.ArgumentParser()
    argp.add_argument('amount', type=str, help='value amount in decimal or whole units')
    argp.add_argument('-t', type=str, choices=['income', 'expense', 'asset', 'liability'], default='income', help='delta type')
    argp.add_argument('-u', type=str, default='USD', help='unit of account')
    argp.add_argument('-r', type=str, help='reference')
    argp.add_argument('-p', type=str, help='parent')
    argp.add_argument('-a', type=str, default='Miscellaneous', help='account')
    argp.add_argument('--date', type=lambda d: datetime.date.fromisoformat(d), default=str(now.date()), help='date of transaction')
    argp.add_argument('--xml-file', dest='xml_file', type=str, default='running.xml', help='xml file to manipulate')
    arg = argp.parse_args()

    tree = lxml.etree.parse(arg.xml_file)
    root = tree.getroot()
    units = get_units(root)
    ledger = init_ledger(root, units)
    
    amount = units.from_floatstring(arg.u, arg.amount, allow_negative=False)

    entry = Entry(arg.t, amount, arg.u, ledger.state.serial + 1, arg.a, arg.date, parent=ledger.state.base)
    wallet = DemoWallet(privatekey=seed)
    entry.sign(wallet)
    ledger.add_entry(entry)
    tree = ledger.to_tree()
    r = lxml.etree.tostring(tree, method='c14n2', strip_text=True)
    print(r.decode('utf-8'))
