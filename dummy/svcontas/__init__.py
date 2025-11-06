import sys
import logging
import datetime
import uuid
import hashlib

from lxml import etree
import rencode

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

DEFAULTPARENT = b'\x00' * 64


class NoopSigVerifier:

    def verify(self, msg, key, sig):
        logg.warning('using noop verifier')
        return True 


class UnitIndex:

    def __init__(self, base):
        self.base = base
        self.detail = {}
        self.exchange = {}


    @staticmethod
    def from_tree(tree):
        r = UnitIndex(tree.get('base'))
        for o in tree.iter('unit'):
            r.detail[o.get('sym')] = int(o.find('precision').text)
            r.exchange[o.get('sym')] = int(o.find('ex').text)
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
    def __init__(self, typ, amount, unit, serial, account, tx_date, ref=None, description=None, parent=None):
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
        self.dtreg = datetime.datetime.now()
        self.attachment = []
        self.sigs = {}
        self.description = description


    def attach(self, mime, algo, digest, description=None, slug=None):
        self.attachment.append((mime, algo, digest, description, slug,))


    def add_signature(self, keyid, sigdata):
        self.sigs[keyid] = sigdata


    @staticmethod
    def from_tree(tree, unitindex):
        o = tree.find('data')
        amount = int(o.find('amount').text)
        unit = unitindex.get(o.find('unit').text)
        serial = int(o.find('serial').text)
        account = o.find('account').text
        dt = datetime.date.fromisoformat(o.find('date').text)
        r = Entry(tree.get('type'), amount, unit, serial, account, dt)
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
        return rencode.dumps(d)


    def package(self, wallet):
        b = self.serialize()
        h = hashlib.new('sha512')
        h.update(b)
        z = h.digest()
        r = wallet.sign(z)
        pubk_hx = wallet.pubkey().hex()
        self.sigs[pubk_hx] = r
        logg.debug('added signature from key {}'.format(pubk_hx))
        return (b, z, r,)


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
        o.text = self.dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        data.append(o)
        
        o = etree.Element('account')
        o.text = self.account
        data.append(o)

        if self.description:
            o = etree.Element('description')
            o.text = self.account
            data.append(o)

        o = etree.Element('amount')
        o.text = self.account
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

    def __init__(self, base, unitindex, verifier=None, tree=None):
        self.uidx = unitindex
        self.base = bytes.fromhex(base)
        self.sigs = {}
        if verifier == None:
            verifier = NoopSigVerifier()
        self.verifier = verifier
        self.entries = {}
        self.running = {}
        self.tree = tree
   

    def add_entry_from_tree(self, tree):
        o = tree.find('data/parent')


    def add_entry(self, entry):
        self.running[entry.unit].apply_entry(entry)
        try:
            entries = self.entries[entry.serial]
        except KeyError:
            self.entries[entry.serial] = []
            entries = self.entries[entry.serial]
        self.entries[entry.serial].append(entry)


    def add_signature(self, sigdata, identity):
        self.verifier.verify(self.base, identity, sigdata)
        self.sigs[identity] = sigdata 
        logg.debug('add sig from key{}: {}'.format(identity, sigdata))

   
    @staticmethod
    def from_tree(tree, unitindex, verifier=None):
        o = tree.find('digest').text # verify that is sha512
        r = Ledger(o, unitindex, verifier=verifier, tree=tree)
        for sig in tree.iter('sig'):
            keyid = sig.get('keyid')
            digest = sig.text
            r.add_signature(digest, keyid)

        o = tree.find('real')
        asset = int(o.find('asset').text)
        liability = int(o.find('liability').text)
        r.real = RunningTotal('.', unitindex, asset=asset, liability=liability)
        logg.debug(r.real)

        for v in tree.iter('virt'):
            income = int(v.find('income').text)
            expense = int(v.find('expense').text)
            asset = int(v.find('asset').text)
            liability = int(v.find('liability').text)
            sym = v.get('symbol')
            r.running[sym] = RunningTotal(sym, unitindex, income=income, expense=expense, asset=asset, liability=liability)
            logg.debug(r.running[sym])

        return r.check()


    def apply_tree(self, tree):
        for v in tree.iter('entry'):
            o = Entry.from_tree(v, self.uidx)
            self.entries[o.serial] = o
            self.running[o.unit].apply_entry(o)


    def check(self):
        return self


    def __str__(self):
        return "state: " + self.base.hex()


def init_ledger(tree, units):
    o = tree.find('incoming')
    return Ledger.from_tree(o, units)
    

def get_units(tree):
    o = tree.find('units')
    return UnitIndex.from_tree(o)


def load(fp):
    f = open(fp, 'r')
    tree = etree.parse(f)
    f.close()
    return tree.getroot()
