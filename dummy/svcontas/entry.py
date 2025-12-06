import enum
import logging
import datetime
import uuid
import hashlib

from lxml import etree
import rencode

from .constant import DEFAULTPARENT, NSPREFIX
from .crypto import DemoWallet
from .error import ACLError
from .xml import nsmap

logg = logging.getLogger('svcontas.entry')


class KeyStoreFormat(enum.IntEnum):
    LITERAL = 0
    INDEXED = 1


class EntryPart:

    def __init__(self, typ, account, amount, src=False):
        self.typ = typ
        self.account = account
        self.amount = amount
        self.issrc = src


    @staticmethod
    def from_tree(tree, src=False):
        typ = tree.get('type')
        amount = int(tree.find('amount', namespaces=nsmap()).text)
        account = tree.find('account', namespaces=nsmap()).text
        return EntryPart(typ, account, amount, src=src)

    
    def apply_tree(self, tree):
        tag = 'dst'
        if self.issrc:
            tag = 'src'
        part = etree.Element(tag, type=self.typ)
        o = etree.Element('account')
        o.text = self.account
        part.append(o)

        o = etree.Element('amount')
        o.text = str(self.amount)
        part.append(o)

        tree.append(part)
        return part


    def __str__(self):
        pfx = 'dst'
        if self.issrc:
            pfx = 'src'
        return '[{}] {}:{} {}'.format(pfx, self.typ, self.account, self.amount)


class Entry:

    # TODO: parent only 0 if serial 0  
    def __init__(self, src, dst, unit, serial, tx_date, ref=None, description=None, parent=None, tx_datereg=None):
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
        self.unit = unit
        self.serial = serial
        self.dt = tx_date
        if tx_datereg == None:
            tx_datereg = datetime.datetime.now()
        self.dtreg = tx_datereg
        self.attachment = []
        self.sigs = {}
        self.description = description
        self.src = src
        self.dst = dst


    def attach(self, mime, algo, digest, description=None, slug=None):
        self.attachment.append((mime, algo, digest, description, slug,))


    def add_signature(self, keyid, sigdata):
        self.sigs[keyid] = sigdata


    @staticmethod
    def from_tree(tree, unitindex, min=0):
        o = tree.find('data', namespaces=nsmap())
        serial = int(o.find('serial', namespaces=nsmap()).text)
        if min > serial:
            raise ValueError('entry serial preceeds ledger')
        unit = o.find('unit', namespaces=nsmap()).text
        unitindex.sym(unit)

        ref = o.find('ref', namespaces=nsmap()).text
        parent = o.find('parent', namespaces=nsmap()).text
        description = o.find('description', namespaces=nsmap())
        if description != None:
            description = description.text
        dt = datetime.date.fromisoformat(o.find('date', namespaces=nsmap()).text)
        dtreg = datetime.datetime.strptime(o.find('dateTimeRegistered', namespaces=nsmap()).text, '%Y-%m-%dT%H:%M:%SZ')
        src = EntryPart.from_tree(tree.find('src', namespaces=nsmap()), src=True)
        dst = EntryPart.from_tree(tree.find('dst', namespaces=nsmap()))

        r = Entry(src, dst, unit, serial, dt, ref=ref, parent=parent, tx_datereg=dtreg, description=description)
        for sig in tree.iter(NSPREFIX + 'sig'):
            r.add_signature(sig.get('keyid'), bytes.fromhex(sig.text))
        return r


    def serialize(self):
        src = [self.src.typ, self.src.account, self.src.amount]
        dst = [self.dst.typ, self.dst.account, self.dst.amount]
        d = [
                self.parent,
                self.serial,
                self.ref,
                self.dtreg.strftime('%Y%m%d%H%M%S'),
                self.dt.strftime('%Y%m%d'),
                self.unit,
                self.description,
                src,
                dst,
                ]
        logg.debug('serialize entry {}'.format(d))
        return rencode.dumps(d)

    
    @staticmethod
    def deserialize(data):
        v = rencode.loads(data)
        parent = v[0]
        serial = v[1]
        ref = v[2]
        date_reg = datetime.datetime.strptime(v[3].decode('utf-8'), '%Y%m%d%H%M%S')
        date = datetime.datetime.strptime(v[4].decode('utf-8'), '%Y%m%d')
        unit = v[5]
        description = v[6]
        src_data = v[7]
        dst_data = v[8]
        src = EntryPart(src_data[0], src_data[1], src_data[2], src=True)
        dst = EntryPart(dst_data[0], dst_data[1], dst_data[2])
        return Entry(src, dst, unit, serial, date, ref=ref, description=description, parent=parent, tx_datereg=date_reg)
        

    def sum(self):
        b = self.serialize()
        h = hashlib.new('sha512')
        h.update(b)
        return (h.digest(), b)


    def sign(self, wallet):
        (z, b) = self.sum()
        r = wallet.sign(z)
        pubk_hx = wallet.pubkey().hex()
        self.sigs[pubk_hx] = r
        logg.debug('added signature from key {}'.format(pubk_hx))
        return (z, r, b,)


    def wrap(self, wallet):
        (digest, sig, data) = self.sign(wallet)
        pubkey = wallet.pubkey()
        d = [
                [
                    KeyStoreFormat.LITERAL.value,
                    pubkey,
                    ],
                sig,
                data,
            ]
        return rencode.dumps(d)


    @staticmethod
    def unwrap(data, acl=None):
        v = rencode.loads(data)
        pubkey_bytes = v[0][1]
        if acl != None:
            label = None
            try:
                label = acl.have(pubkey_bytes)
            except KeyError:
                raise ACLError()
            if not acl.may(label, 0x01):
                raise ACLError()
        wallet = DemoWallet(publickey=pubkey_bytes)
        sig = v[1]
        entry = Entry.deserialize(v[2])
        (z, b) = entry.sum()
        wallet.verify(z, sig)
        return entry



    def to_tree(self):
        #tree = etree.Element('entry', type=self.typ)
        tree = etree.Element('entry')
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
        
        if self.description:
            o = etree.Element('description')
            o.text = self.description
            data.append(o)

        self.src.apply_tree(tree)
        self.dst.apply_tree(tree)
        
        tree.append(data)

        for k in self.sigs.keys():
            o = etree.Element('sig', type='ed25519', keyid=k)
            o.text = self.sigs[k].hex()
            tree.append(o)

        return tree
