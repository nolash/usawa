import argparse
import datetime

import lxml.etree
import confini
import nacl.signing

from svcontas import Ledger, Entry, DemoWallet, get_units, init_ledger


seed = bytes.fromhex('2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae')
#pubk = pk.verify_key

state_serial = 0
state_digest = b'00' * 64


def save_state():
    f = open('.state', 'wb')
    b = state_serial.to_bytes(8, byteorder='big')
    f.write(b)
    f.close()
    return state_serial


def load_state():
    try:
        f = open('.state', 'rb')
    except FileNotFoundError:
        return save_state()
    b = f.read(8)
    f.close()
    state_serial = int.from_bytes(b, byteorder='big')
    return state_serial


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

    load_state()
    tree = lxml.etree.parse(arg.xml_file)
    root = tree.getroot()
    units = get_units(root)
    ledger = init_ledger(root, units)
    
    amount = units.from_floatstring(arg.u, arg.amount, allow_negative=False)

    state_serial += 1
    entry = Entry(arg.t, amount, arg.u, state_serial, arg.a, arg.date)
    wallet = DemoWallet(privatekey=seed)
    entry.sign(wallet)
    ledger.add_entry(entry)
    #r = lxml.etree.tostring(entry.to_tree())
    #print(r.decode('utf-8'))
    tree = ledger.to_tree()
    r = lxml.etree.tostring(tree, method='c14n2', strip_text=True)
    print(r.decode('utf-8'))

    save_state()
