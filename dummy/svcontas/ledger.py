import datetime
import logging

import lxml

from .crypto import DemoWallet
from .xml import nsmap
from .state import State
from .constant import NSPREFIX, DEFAULTPARENT
from .entry import Entry

logg = logging.getLogger('svcontas.ledger')


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

    def __init__(self, serial, base, unitindex, tree=None, acl=None):
        self.uidx = unitindex
        self.sigs = {}
        self.entries = {}
        self.running = {}
        self.tree = tree
        if self.tree == None:
            self.reset()
        self.state = State()
        self.state.poke(serial, base)
        self.acl = acl


    def reset(self, src='defalsify.org'):
        self.entries[self.uidx.base] = []
        self.running[self.uidx.base] = RunningTotal(self.uidx.base, self.uidx)
        self.tree = lxml.etree.XML('<ledger xmlns="http://svcontas.defalsify.org/"></ledger>')
        #self.tree = lxml.etree.Element('ledger', nsmap=nsmap())
        o = lxml.etree.SubElement(self.tree, NSPREFIX + 'retrieved', nsmap=nsmap())
        o.text = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%dT%H:%M:%SZ')
        #self.tree.append(o)
        o = lxml.etree.SubElement(self.tree, NSPREFIX + 'src', nsmap=nsmap())
        o.text = src

        units = lxml.etree.SubElement(self.tree, NSPREFIX + 'units', nsmap=nsmap())
        units.attrib['base'] = self.uidx.base
        for v in self.uidx.syms():
            unit = lxml.etree.SubElement(units, NSPREFIX + 'unit', nsmap=nsmap())
            unit.attrib['sym'] = v
            o = lxml.etree.SubElement(unit, NSPREFIX + 'precision', nsmap=nsmap())
            o.text = str(self.uidx.get(v))
            #unit.append(o)
            o = lxml.etree.SubElement(unit, NSPREFIX + 'exchange', nsmap=nsmap())
            o.text = str(self.uidx.ex(v))
            #unit.append(o)
            #units.append(unit)
        #self.tree.append(units)

        incoming = lxml.etree.SubElement(self.tree, NSPREFIX + 'incoming', nsmap=nsmap())
        incoming.attrib['serial'] = '0'

        real = lxml.etree.SubElement(incoming, NSPREFIX + 'real', nsmap=nsmap())
        real.attrib['unit'] = self.uidx.base
        o = lxml.etree.SubElement(real, NSPREFIX + 'asset', nsmap=nsmap())
        o.text = '0'
        #real.append(o)
        o = lxml.etree.SubElement(real, NSPREFIX + 'liability', nsmap=nsmap())
        o.text = '0'
        #real.append(o)
        #incoming.append(real)

        o = lxml.etree.SubElement(incoming, NSPREFIX + 'digest', nsmap=nsmap())
        o.attrib['algo'] = 'sha512'
        o.text = DEFAULTPARENT.hex()
        #incoming.append(o)
        #self.tree.append(incoming)


    # TODO: should append after last
    def add_identity(self, keyid, did, typ='web'):
        root = self.tree
        tree = root.find('resolver', namespaces=nsmap())
        if tree == None:
            tree = root.find('units', namespaces=nsmap())
            if tree == None:
                logg.debug('exception tree {}'.format(lxml.etree.tostring(self.tree)))
                raise Exception('cannot find units node')
        o = lxml.etree.Element(NSPREFIX + 'identity', nsmap=nsmap())
        o.attrib['keyid'] = keyid
        o.attrib['didtype'] = typ
        o.text = did
        tree.addnext(o)
   

    # TODO: should append after last
    def add_resolver(self, uri, algo='sha256', proto='https'):
        tree = self.tree.find('units', namespaces=nsmap())
        o = lxml.etree.Element(NSPREFIX + 'resolver', nsmap=nsmap())
        o.attrib['algo'] = algo
        o.attrib['proto'] = proto
        o.text = uri
        tree.addnext(o)


    # TODO: add check against trusted pubkey list
    def check_sigs(self, entry):
        have = False
        valid_keys = None
        if self.acl == None:
            valid_keys = list(entry.sigs.keys())
        else:
            valid_keys = list(self.acl.pubkeys(binary=False))
        #for k in entry.sigs.keys():
        for k in valid_keys:
            b = bytes.fromhex(k)
            try:
                sig = entry.sigs[k]
            except KeyError:
                continue
            wallet = DemoWallet(publickey=b)
            v = entry.sum()
            r = wallet.verify(v, sig)
            have = True
            logg.debug('having sig {}'.format(r.hex()))
        return have


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
    def from_tree(tree, unitindex, acl=None):
        part = tree.find('incoming', namespaces=nsmap())
        serial = int(part.get('serial'))
        o = part.find('digest', namespaces=nsmap()).text # verify that is sha512
        r = Ledger(serial, bytes.fromhex(o), unitindex, tree=tree, acl=acl)

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


    def to_string(self):
        return lxml.etree.tostring(self.tree)


    def __str__(self):
        return "state: " + self.state.base.hex()
