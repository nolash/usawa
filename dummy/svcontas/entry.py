import logging
import datetime
import uuid
import hashlib

from lxml import etree
import rencode

from .constant import DEFAULTPARENT, NSPREFIX
from .xml import nsmap

logg = logging.getLogger('svcontas.entry')


class Entry:

    # TODO: parent only 0 if serial 0  
    def __init__(self, typ, amount, unit, serial, account, tx_date, ref=None, description=None, parent=None, tx_datereg=None):
        self.typ = typ
        if isinstance(parent, str):
            parent = bytes.fromhex(parent)
        elif parent == None:
            parent = DEFAULTPARENT
        elif len(parent) != 64:
            raise ValueError('invalid parent hash')
        if ref == None:
            ref = str(uuid.uuid4())
        self.ref = ref
        self.parent = parent
        self.amount = amount
        self.unit = unit
        self.serial = serial
        self.account = account
        self.dt = tx_date
        if tx_datereg == None:
            tx_datereg = datetime.datetime.now()
        self.dtreg = tx_datereg
        self.attachment = []
        self.sigs = {}
        self.description = description


    def attach(self, mime, algo, digest, description=None, slug=None):
        self.attachment.append((mime, algo, digest, description, slug,))


    def add_signature(self, keyid, sigdata):
        self.sigs[keyid] = sigdata


    @staticmethod
    def from_tree(tree, unitindex):
        o = tree.find('data', namespaces=nsmap())
        amount = int(o.find('amount', namespaces=nsmap()).text)
        unit = unitindex.get(o.find('unit', namespaces=nsmap()).text)
        serial = int(o.find('serial', namespaces=nsmap()).text)
        account = o.find('account', namespaces=nsmap()).text
        ref = o.find('ref', namespaces=nsmap()).text
        parent = o.find('parent', namespaces=nsmap()).text
        description = o.find('description', namespaces=nsmap())
        if description != None:
            description = description.text
        dt = datetime.date.fromisoformat(o.find('date', namespaces=nsmap()).text)
        dtreg = datetime.datetime.strptime(o.find('dateTimeRegistered', namespaces=nsmap()).text, '%Y-%m-%dT%H:%M:%SZ')
        r = Entry(tree.get('type'), amount, unit, serial, account, dt, ref=ref, parent=parent, tx_datereg=dtreg, description=description)
        for sig in tree.iter(NSPREFIX + 'sig'):
            r.add_signature(sig.get('keyid'), bytes.fromhex(sig.text))
        return r


    def serialize(self):
        d = [
                self.parent,
                self.serial,
                self.ref,
                self.dtreg.strftime('%Y%m%d%H%M%S'),
                self.dt.strftime('%Y%m%d'),
                self.unit,
                self.amount,
                ]
        logg.debug('serialize entry {}'.format(d))
        return rencode.dumps(d)


    def sum(self):
        b = self.serialize()
        h = hashlib.new('sha512')
        h.update(b)
        return h.digest()


    def sign(self, wallet):
        b = self.sum()
        r = wallet.sign(b)
        pubk_hx = wallet.pubkey().hex()
        self.sigs[pubk_hx] = r
        logg.debug('added signature from key {}'.format(pubk_hx))
        return (b, r,)


    def to_tree(self):
        tree = etree.Element('entry', type=self.typ)
        data = etree.Element('data')

        o = etree.Element('parent')
        o.text = self.parent.hex()
        data.append(o)

        o = etree.Element('ref')
        o.text = self.ref
        data.append(o)

        o = etree.Element('serial')
        o.text = str(self.serial)
        data.append(o)

        o = etree.Element('unit')
        o.text = self.unit 
        data.append(o)

        o = etree.Element('date')
        o.text = self.dt.strftime('%Y-%m-%d')
        data.append(o)

        o = etree.Element('dateTimeRegistered')
        o.text = self.dtreg.strftime('%Y-%m-%dT%H:%M:%SZ')
        data.append(o)
        
        o = etree.Element('account')
        o.text = self.account
        data.append(o)

        if self.description:
            o = etree.Element('description')
            o.text = self.account
            data.append(o)

        o = etree.Element('amount')
        o.text = str(self.amount)
        data.append(o)

        tree.append(data)

        for k in self.sigs.keys():
            o = etree.Element('sig', type='ed25519', keyid=k)
            o.text = self.sigs[k].hex()
            tree.append(o)

        return tree



