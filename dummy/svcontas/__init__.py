import sys
import logging
import datetime
import uuid
import hashlib

from lxml import etree
import rencode
import nacl.signing

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

DEFAULTPARENT = b'\x00' * 64
NS = 'http://svcontas.defalsify.org'
NAMESPACES = {None: NS}
NSPREFIX = '{' + NS + '}'

def nsmap():
    return NAMESPACES

class State:

    def __init__(self):
        self.serial = 0
        self.base = DEFAULTPARENT


    def poke(self, serial, base):
        if serial > self.serial:
            logg.debug('new latest state {} {}'.format(serial, base.hex()))
            self.serial = serial
            self.base = base
        return self.serial


    def save(self):
        f = open('.state', 'wb')
        b = self.serial.to_bytes(8, byteorder='big')
        f.write(b)
        f.close()
        return self.serial


    def load(self):
        try:
            f = open('.state', 'rb')
        except FileNotFoundError:
            return self.save()
        b = f.read(8)
        f.close()
        self.serial = int.from_bytes(b, byteorder='big')
        return self.serial


class DemoWallet:

    def __init__(self, privatekey=None, publickey=None):
        publickey_chk = None
        if privatekey == None:
            if publickey == None:
                privatekey = nacl.signing.SigningKey.generate()
        if privatekey != None:
            self.pk = nacl.signing.SigningKey(privatekey)
            publickey_chk = self.pk.verify_key
        if publickey == None:
            if publickey_chk == None:
                raise AttributeError('wallet must be created with either public or private key')
            publickey = publickey_chk    
        elif publickey_chk != None and publickey != publickey_chk.encode():
            raise ValueError('publickey supplied does not match privatekey')
        else:
            publickey = nacl.signing.VerifyKey(publickey)
        self.pubk = publickey
   
    def sign(self, v):
        r = self.pk.sign(v)
        return r.signature


    def pubkey(self):
        return self.pubk.encode()


    def verify(self, v, sig):
        return self.pubk.verify(v, sig)


class UnitIndex:

    def __init__(self, base):
        self.base = base
        self.detail = {}
        self.exchange = {}


    @staticmethod
    def from_tree(tree):
        r = UnitIndex(tree.get('base'))
        logg.debug('base {}'.format(tree))
        for o in tree.iter(NSPREFIX + 'unit'):
            logg.debug('add unit ' + o.get('sym'))
            r.detail[o.get('sym')] = int(o.find('precision', namespaces=nsmap()).text)
            r.exchange[o.get('sym')] = int(o.find('ex', namespaces=nsmap()).text)
        r.check()
        return r


    def check(self):
        self.get(self.base)
        return self


    def get(self, k):
        self.detail[k]
        return k


    def to_floatstring(self, sym, v, allow_negative=True):
        neg = v < 0
        if neg and not allow_negative:
            raise ValueError('negative value not allowed')
        v = abs(v)
        c = self.detail[sym]
        i = c * -1
        s = str(v)
        l = len(s)
        if l < c:
            ss = '0' * c
            s = '0' + ss[:c-l] + s
        r = s[:i] + '.' + s[i:]
        if neg:
            r = '-' + r
        return r


    def from_floatstring(self, sym, v, allow_negative=True):
        neg = False
        if v[0] == '-':
            if not allow_negative:
                raise ValueError('negative value not allowed')
            neg = True
            v = v[1:]
        c = self.detail[sym]
        s = v.split('.')
        if len(s) == 1:
            return int(s[0]) * (10**c)
        r = s[1]
        l = len(r)
        if l < c:
            r += '0' * (c - l)
        r = s[0] + r
        if neg:
            r *= -1
        return int(r)


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


class RunningTotal:

    def __init__(self, sym, unitindex, asset=0, liability=0, income=0, expense=0):
        self.sym = sym
        self.asset = asset
        self.liability = liability
        self.income = income
        self.expense = expense
        self.unitindex = unitindex


    def get_balance(self):
        return self.asset - self.liability 


    def get_result(self):
        return self.income - self.expense


    def income_delta(self, v):
        self.income += v
        self.asset += v


    def expense_delta(self, v):
        self.expense += v
        self.asset -= v


    def asset_delta(self, v):
        self.asset += v


    def liability_delta(self, v):
        self.liability += v


    def apply_entry(self, entry):
        fn = getattr(self, entry.typ + '_delta')
        fn(entry.amount)
        logg.debug('applied entry {} typ {} amount {} total {} balance {}'.format(entry.serial, entry.typ, entry.amount, getattr(self, entry.typ), self.unitindex.to_floatstring(self.sym, self.get_balance())))


    def __str__(self):
        return 'running total {}: income {} expense {} asset {} liability {}'.format(self.sym, self.income, self.expense, self.asset, self.liability)


class Ledger:

    def __init__(self, serial, base, unitindex, tree=None):
        self.uidx = unitindex
        self.sigs = {}
        self.entries = {}
        self.running = {}
        self.tree = tree
        self.state = State()
        self.state.poke(serial, base)
   

    # TODO: add check against trusted pubkey list
    def check_sigs(self, entry):
        for k in entry.sigs.keys():
            b = bytes.fromhex(k)
            sig = entry.sigs[k]
            wallet = DemoWallet(publickey=b)
            v = entry.sum()
            r = wallet.verify(v, sig)
            logg.debug('having sig {}'.format(r.hex()))
        return True


    def add_entry(self, entry, modify_tree=True):
        if not self.check_sigs(entry):
            raise ValueError('entry must have at least one valid signature')
        try:
            entries = self.entries[entry.serial]
        except KeyError:
            self.entries[entry.serial] = []
            #entries = self.entries[entry.serial]
        self.state.poke(entry.serial, entry.sum())
        self.entries[entry.serial].append(entry)
        self.running[entry.unit].apply_entry(entry)
        if self.tree != None and modify_tree:
            self.tree.append(entry.to_tree())
        logg.debug(self.running[entry.unit])


    def add_signature(self, sigdata, identity):
        self.sigs[identity] = sigdata 
        logg.debug('add sig from key{}: {}'.format(identity, sigdata))

   
    @staticmethod
    def from_tree(tree, unitindex):
        part = tree.find('incoming', namespaces=nsmap())
        serial = int(part.get('serial'))
        o = part.find('digest', namespaces=nsmap()).text # verify that is sha512
        r = Ledger(serial, bytes.fromhex(o), unitindex, tree=tree)

        for sig in part.iter(NSPREFIX + 'sig'):
            keyid = sig.get('keyid')
            digest = sig.text
            r.add_signature(digest, keyid)

        o = part.find('real', namespaces=nsmap())
        asset = int(o.find('asset', namespaces=nsmap()).text)
        liability = int(o.find('liability', namespaces=nsmap()).text)
        r.real = RunningTotal('.', unitindex, asset=asset, liability=liability)
        logg.debug(r.real)

        for v in part.iter(NSPREFIX + 'virt'):
            income = int(v.find('income', namespaces=nsmap()).text)
            expense = int(v.find('expense', namespaces=nsmap()).text)
            asset = int(v.find('asset', namespaces=nsmap()).text)
            liability = int(v.find('liability', namespaces=nsmap()).text)
            sym = v.get('unit')
            r.running[sym] = RunningTotal(sym, unitindex, income=income, expense=expense, asset=asset, liability=liability)
            logg.debug(r.running[sym])

        r.apply_tree(tree)
        return r.check()


    def apply_tree(self, tree):
        for v in tree.iter(NSPREFIX + 'entry'):
            logg.debug('processing entry {}'.format(v))
            o = Entry.from_tree(v, self.uidx)
            self.add_entry(o, modify_tree=False)


    def to_tree(self):
        return self.tree


    def check(self):
        return self


    def __str__(self):
        return "state: " + self.state.base.hex()


def init_ledger(tree, units):
    return Ledger.from_tree(tree, units)
    

def get_units(tree):
    o = tree.find('units', namespaces=nsmap())
    return UnitIndex.from_tree(o)


def load(fp):
    f = open(fp, 'r')
    tree = etree.parse(f)
    f.close()
    return tree.getroot()
