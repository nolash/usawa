import os
import datetime

import logging
import hashlib

import lxml
import rencode
import varints.leb128s

from .crypto import DemoWallet, ACL
from .xml import nsmap, XML_FORMAT_VERSION
from .constant import NSPREFIX, DEFAULTPARENT
from .entry import Entry
from .util import to_datestring

logg = logging.getLogger('usawa.ledger')



class RunningTotal:
    """RunningTotal is used by the Ledger object to keep track of running totals in all asset and transaction categories of a given unit symbol.

    The symbol must exist in the unit index provided.

    All values used in methods of this object must be integer values representing the decimals corresponding to the precision of the symbol, as defined by the unit index.

    :param sym: Unit symbol tracked by this object.
    :type sym: str
    :param unitindex: Unit index to resolve symbol against.
    :type unitindex: usawa.UnitIndex
    :param asset: Initial asset total.
    :type asset: int
    :param liability: Initial liability total.
    :type liability: int
    :param income: Initial income total.
    :type income: int
    :param expense: Initial expense total.
    :type expense: int
    :todo: Specify raises when sym not found in unitindex.
    """

    def __init__(self, sym, unitindex, asset=0, liability=0, income=0, expense=0):
        self.sym = sym
        self.asset = asset
        self.liability = liability
        self.income = income
        self.expense = expense
        self.unitindex = unitindex


    """Return the current asset/liability balance.

    :returns: Balance
    :rtype: int
    """
    def get_balance(self):
        return self.asset - self.liability 

    """Return the current income/expense result.

    :returns: Result. 
    :rtype: int
    """
    def get_result(self):
        return self.income - self.expense


    """Increment the income total by the provided value.

    :param v: Value
    :type v: int
    """
    def income_delta(self, v):
        self.income += v

    """Increment the expense total by the provided value.

    :param v: Value
    :type v: int
    """
    def expense_delta(self, v):
        self.expense += v

    """Increment the asset total by the provided value.

    :param v: Value
    :type v: int
    """
    def asset_delta(self, v):
        self.asset += v

    """Increment the liability total by the provided value.

    :param v: Value
    :type v: int
    """
    def liability_delta(self, v):
        self.liability += v


    """Apply all deltas from an entry to the running total.

    The running total does not keep track of which entries have been applied.

    :param entry: Entry to apply changes for.
    :type entry: usawa.Entry
    """
    def apply(self, typ, amount):
        fn = getattr(self, typ + '_delta')
        fn(amount)



    """
    """
    def from_tree(tree):
        unit = self.tree.get('unit')
        asset = int(self.tree.find('asset', namespaces=nsmap()).text)
        liability = int(self.tree.find('liability', namespaces=nsmap()).text)
        return RunningTotal(unit, asset=asset, liability=liability)


    """
    """
    def serialize(self):
        d = [
                self.sym,
                varints.leb128s.encode(self.income),
                varints.leb128s.encode(self.expense),
                varints.leb128s.encode(self.asset),
                varints.leb128s.encode(self.liability),
                ]
        return rencode.dumps(d)



    def __str__(self):
        return 'running total {}: income {} expense {} asset {} liability {}'.format(self.sym, self.income, self.expense, self.asset, self.liability)


class Ledger:

    default_src = 'defalsify.org'

    """Ledger represents a signed and verified chain of transaction entries.

    Apart from the entries chain, it also holds metadata required to expand underlying assets referenced by the entries, aswell as resolution and verification of identities of signatories.

    If populated by an XML tree, all unit definitions encountered will be added to the provided UnitIndex. All other parameters will be ignored.

    If the serial number parameter is non-zero, the base must be a non-zero digest value.

    :param unitindex: The unit index to resolve transaction values used in the entries.
    :type unitindex: usawa.UnitIndex
    :param tree: A verified XML tree to use to populate the ledger.
    :type tree: lxml.etree.ElementTree
    :param acl: A collection of public keys to use to verify signatures. Will override existing public key lists.
    :type acl: usawa.ACL
    :param serial: Serial number to start the current state of the ledger on.
    :type serial: int
    :param base: Hexadecimal digest value defining the state of the ledger at the corresponding serial number. The digest type is defined in usawa.Entry.digest_algo
    :type base: str
    :param topic: Hexadecimal userdata providing context of the ledger.
    :type topic: str
    :todo: Add warnings for ignored parameters
    """

    def __init__(self, unitindex, tree=None, acl=None, serial=1, base=DEFAULTPARENT, topic=None, src=None, wallet=None):
        self.uidx = unitindex
        self.sigs = {}
        self.entries = {}
        self.running = {}
        self.resolvers = {}
        self.tree = tree
        self.base = base
        self.base_serial = serial
        self.src = src
        self.topic = topic
        self.acl = acl
        self.dt = None
        self.wallet = wallet
        if self.topic == None:
            self.topic = os.urandom(64)
        if base == None:
            h = hashlib.sha512()
            h.update(topic)
            h.update(DEFAULTPARENT)
            base = h.digest()
        if self.tree == None:
            self.reset()
        self.serial = self.base_serial
        self.cur = base
        logg.debug('ledger base {} serial {} from topic {}'.format(self.base.hex(), self.serial, self.topic.hex()))


    """Wallet to add public key for in identities element in ledger XML.

    :param v: Wallet to set
    :type v: usawa.Wallet
    """
    def set_wallet(self, v):
        self.wallet = v
        if self.acl == None:
            self.acl = ACL.from_wallet(self.wallet)
        self.apply_wallet()


    def apply_wallet(self):
        incoming = self.tree.find('incoming', namespaces=nsmap()) 
        v = self.wallet.pubkey()
        o = lxml.etree.Element(NSPREFIX + 'identity', nsmap=nsmap())
        o.set('keyid', v.hex())
        did = self.wallet.did()
        o.set('didtype', did.method())
        incoming.addprevious(o)


    """Retrieve the serial that will be assigned to the next entry.

    :rtype: int
    :return: Serial
    """
    def peek(self):
        return self.serial + 1

    """Increment the serial and return the incremented serial, to be used for the next entry.

    :rtype: int
    :return: Serial
    """
    def next_serial(self):
        self.serial += 1
        return self.serial


    """Remove all entries from the ledger, and reset all metadata to defaults.

    If either src or topic is not defined, the existing src or topic value on the existing ledger will be preserved. If none is set, they will be set to default values.

    :param src: URI to the source of ledger information.
    :type src: str
    :param topic: Topic to set for new ledger.
    :type topic: bytes
    :rtype: None
    :todo: swapping tree keeps two trees in memory, perhaps it can be more efficient
    :todo: add permissions array to the identities elements
    """
    def reset(self, src=None, topic=None, acl=None, wallet=None):
        if wallet != None:
            self.set_wallet(wallet)
        self.serial = self.base_serial
        self.cur = self.base
        self.entries[self.uidx.base] = []
        tree = lxml.etree.XML('<ledger xmlns="http://usawa.defalsify.org/" version="{}"></ledger>'.format(XML_FORMAT_VERSION))
        if self.tree == None:
            self.tree = tree
        o = lxml.etree.SubElement(tree, NSPREFIX + 'topic', nsmap=nsmap())
        if topic == None:
            if self.topic == None:
                topic = os.urandom(64)
                topic = topic.hex()
            else:
                topic = self.topic.hex()
        o.text = topic
        o = lxml.etree.SubElement(tree, NSPREFIX + 'generated', nsmap=nsmap())
        self.dt = datetime.datetime.now()
        o.text = to_datestring(self.dt)
        #self.tree.append(o)
        o = lxml.etree.SubElement(tree, NSPREFIX + 'src', nsmap=nsmap())
        if src == None:
            if self.src == None:
                src = self.default_src
            else:
                src = self.src
        o.text = src

        units = lxml.etree.SubElement(tree, NSPREFIX + 'units', nsmap=nsmap())
        logg.debug('uidx {} units {} base {}'.format(self.uidx, units, self.uidx.base))
        units.set('base', self.uidx.base)
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

        
        ns = {'ns': nsmap()[None]}

        # TODO: move identity tree generation to wallet object
        identities = []
        for tree_identity in self.tree.xpath('ns:identity', namespaces=ns):
            v = tree_identity.text
            identities.append(v)
            identity = lxml.etree.SubElement(tree, NSPREFIX + 'identity', nsmap=nsmap())
            identity.text = v
            identity.set('keyid', tree_identity.get('keyid'))
            identity.set('didtype', tree_identity.get('didtype'))

        if acl != None:
            for v in acl.pubkeys(binary=False):
            #v = wallet.address()
                if v not in identities:
                    identities.append(v)
                    identity = lxml.etree.SubElement(tree, NSPREFIX + 'identity', nsmap=nsmap())
                    identity.set('keyid', v)
                    identity.set('didtype', acl.did(v).method())

        if len(identities) == 0:
            logg.warning('no identities in xml, need at least one to validate against schema')

        incoming = lxml.etree.SubElement(tree, NSPREFIX + 'incoming', nsmap=nsmap())
        incoming.set('serial', str(self.serial))
        
        # swap running and apply all bases
        self.running = {}
        incoming_old = self.tree.find('incoming', namespaces=nsmap()) 
        logg.debug('inc {}'.format(lxml.etree.tostring(incoming_old)))

        if incoming_old != None:
            i = 0
            for tree_real in incoming_old.xpath('ns:real[@unit]', namespaces=ns):
                unit = tree_real.get('unit')
                v = tree_real.find('asset', namespaces=nsmap())
                asset = int(v.text)
                v = tree_real.find('liability', namespaces=nsmap())
                liability = int(v.text)
                self.running[unit] = RunningTotal(unit, self.uidx, asset=asset, liability=liability)
                real = lxml.etree.SubElement(incoming, NSPREFIX + 'real', nsmap=nsmap())
                real.attrib['unit'] = unit
                o = lxml.etree.SubElement(real, NSPREFIX + 'asset', nsmap=nsmap())
                o.text = str(self.running[unit].asset)
                o = lxml.etree.SubElement(real, NSPREFIX + 'liability', nsmap=nsmap())
                o.text = str(self.running[unit].liability)
                i += 1

            if i == 0:
                real = lxml.etree.SubElement(incoming, NSPREFIX + 'real', nsmap=nsmap())
                real.set('unit', self.uidx.default_unit)
                o = lxml.etree.SubElement(real, NSPREFIX + 'asset', nsmap=nsmap())
                o.text = '0'
                o = lxml.etree.SubElement(real, NSPREFIX + 'liability', nsmap=nsmap())
                o.text = '0'

        for k in self.uidx.syms():
            if self.running.get(k) != None:
                continue
            logg.debug('add new runningtotal for {}'.format(k))
            self.running[k] = RunningTotal(k, self.uidx)

        o = lxml.etree.SubElement(incoming, NSPREFIX + 'digest', nsmap=nsmap())
        o.attrib['algo'] = 'sha512'
        o.text = self.base.hex()

        if self.wallet != None:
            r = self.sign()
            o = lxml.etree.SubElement(incoming, NSPREFIX + 'sig', nsmap=nsmap())
            o.set('keyid', self.wallet.address().hex())
            o.set('type', 'ed25519')
            o.text = r.hex()

        self.tree = tree
        #incoming.append(o)
        #self.tree.append(incoming)


    """Add a decentralized identity definition for signers of the ledger.

    :param keyid: Hexadecimal representation of the key identifier.
    :type keyid: str
    :param did: Did provider.
    :type did: str
    :param typ: Type of did provider, default 'web'.
    :type did: str
    :todo: should append after last
    """
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
   

    """Add an endpoint to resolve content by digest.

    :param location: The endpoint location, host and path or only path, depending on the scheme.
    :type path: str
    :param algo: Digest algorithm to use to retrieve and verify content, default 'sha256'.
    :type path: str
    :param proto: URI scheme used to connect to the endpoint.
    :param algo: str
    :todo: should append after last
    """
    def add_resolver(self, location, algo='sha256', scheme='https'):
        tree = self.tree.find('units', namespaces=nsmap())
        o = lxml.etree.Element(NSPREFIX + 'resolver', nsmap=nsmap())
        o.attrib['algo'] = algo
        o.attrib['proto'] = proto
        o.text = location

        if self.resolvers.get(algo) == None:
            self.resolvers[algo] = []
        self.resolvers[algo].append((proto, location,))

        tree.addnext(o)

    """Check signature on individual ledger entry.

    :param entry: The individual entry to verify.
    :type entry: usawa.Entry
    """
    def check_sigs(self, entry):
        have = False
        valid_keys = None
        if self.acl == None:
            logg.debug('no acl in ledger')
            valid_keys = list(entry.sigs.keys())
        else:
            valid_keys = list(self.acl.pubkeys(binary=False))
        logg.debug('testing valid keys {}'.format(valid_keys))
        for k in valid_keys:
            b = None
            try:
                b = bytes.fromhex(k)
            except:
                b = k
            try:
                sig = entry.sigs[k]
            except KeyError:
                logg.debug('no signature from {}'.format(k))
                continue
            wallet = DemoWallet(publickey=b)
            v = entry.sum()
            return wallet.verify(v[0], sig)
        #return have


    """Append entry to ledger. The entry must have a valid signature from a trusted public key.

    :param entry: The entry to append.
    :type entry: usawa.Entry
    :param modify_tree: If True, also append the entry to the XML export.
    :type modify_tree: boolean
    :raises ValueError: When entry parent does not match ledger state.
    :raises PermissionError: When entry is missing valid signature.
    :todo: modify_tree is too low-level for this API
    """
    def add_entry(self, entry, modify_tree=True):
        if self.cur != entry.parent:
            raise ValueError('entry parent does not match ledger state')
        if not self.check_sigs(entry):
            raise PermissionError('entry must have at least one valid signature')
        try:
            entries = self.entries[entry.serial]
        except KeyError:
            self.entries[entry.serial] = []
            #entries = self.entries[entry.serial]
        self.serial = entry.serial
        oldbase = self.base
        self.cur = entry.sum()[0]
        entry.parent = oldbase
        self.entries[entry.serial].append(entry)
        #self.running[entry.unit].apply_entry(entry)
        self.apply_entryparts(entry)
        if self.tree != None and modify_tree:
            entry_tree = entry.to_tree()
            self.tree.append(entry_tree)


    def apply_entryparts(self, entry):
        for v in entry.debit:
#        src = entry.src.typ
#        dst = entry.dst.typ
#        src_isbalance = src in ['liability', 'asset']
#        dst_isbalance = dst in ['liability', 'asset']
#        src_unit = entry.src.unit
#        dst_unit = entry.dst.unit
            amount = v.amount
            if v.isdebit:
                amount *= -1
            self.running[v.unit].apply(v.typ, amount)

        for v in entry.credit:
            amount = v.amount
            if v.isdebit:
                amount *= -1
            self.running[v.unit].apply(v.typ, amount)
        
#        src_amount = entry.src.amount
#        dst_amount = entry.dst.amount
#        if src_isbalance and dst_isbalance:
#            if dst == 'liability':
#                src_amount *= -1
#                dst_amount *= -1
#        self.running[src_unit].apply(src, src_amount)
#        self.running[dst_unit].apply(dst, dst_amount)

        logg.debug('applied entry {} src {} dst {}'.format(entry.serial, entry.debit, entry.credit))


    def apply_signature(self, identity):
        sig = self.sigs[identity]
        tree = self.tree.find('incoming', namespaces=nsmap())
        o = lxml.etree.SubElement(tree, NSPREFIX + 'sig', nsmap=nsmap())
        o.set('keyid', identity.hex())
        o.set('type', 'ed25519')
        o.text = sig.hex()
        

    """Add a signature on the ledger.
    
    :todo: not an appropriate API function?
    :todo: implement validity checks for signature.
    """
    def add_signature(self, sigdata, identity, modify_tree=True):
        self.sigs[identity] = sigdata
        if modify_tree:
            self.apply_signature(identity)
        logg.debug('add sig from key {}: {}'.format(identity.hex(), sigdata.hex()))

  
    """Create a new ledger from a parsed XML document.

    Does not check validity of tree against schema.

    :param tree: A parsed and validated XML tree.
    :type tree: lxml.etree.ElementTree
    :param unitindex: Definition of all units used in the XML tree.
    :type unitindex: usawa.UnitIndex
    :param acl: List of public keys to validate signatures against. Overrides the keys in the entry object.
    :type acl: usawa.ACL
    :todo: Specify in docs which exception raised if unit not found in index.
    """
    @staticmethod
    def from_tree(tree, unitindex, acl=None):
        topic_node = tree.find('topic', namespaces=nsmap())
        topic = bytes.fromhex(topic_node.text)

        units = tree.find('units', namespaces=nsmap())
        unit = units.get('base')
        part = tree.find('incoming', namespaces=nsmap())
        serial = int(part.get('serial'))
        o = part.find('digest', namespaces=nsmap()).text # verify that is sha512
        r = Ledger(unitindex, topic=topic, tree=tree, acl=acl, serial=serial, base=bytes.fromhex(o))

        for sig in part.iter(NSPREFIX + 'sig'):
            keyid = sig.get('keyid')
            digest = sig.text
            r.add_signature(bytes.fromhex(digest), bytes.fromhex(keyid), modify_tree=False)

        o = part.find('real', namespaces=nsmap())
        asset = int(o.find('asset', namespaces=nsmap()).text)
        liability = int(o.find('liability', namespaces=nsmap()).text)
        r.real = RunningTotal(unit, unitindex, asset=asset, liability=liability)

        for v in part.iter(NSPREFIX + 'virt'):
            income = int(v.find('income', namespaces=nsmap()).text)
            expense = int(v.find('expense', namespaces=nsmap()).text)
            asset = int(v.find('asset', namespaces=nsmap()).text)
            liability = int(v.find('liability', namespaces=nsmap()).text)
            sym = v.get('unit')
            r.running[sym] = RunningTotal(sym, unitindex, income=income, expense=expense, asset=asset, liability=liability)
            logg.debug(r.running[sym])

        if r.running.get(unit) == None:
            r.running[unit] = RunningTotal(unit, unitindex)

        r.apply_tree(tree)
        logg.debug('loaded ledger tree last serial {}'.format(r.serial))
        return r.check()


    """Append all entries from XML tree to ledger.

    :param tree: A parsed XML tree.
    :todo: Not an API method.
    """
    def apply_tree(self, tree):
        start = self.serial
        last = 1
        i = 0
        for v in tree.iter(NSPREFIX + 'entry'):
            i += 1
            logg.debug('processing entry {}'.format(v))
            o = Entry.from_tree(v, self.uidx, min=self.serial)
            self.add_entry(o, modify_tree=False)
            if o.serial > last:
                last = o.serial
        if i > 0:
            self.serial = last
        logg.info('last entry from tree serial ' + str(self.serial))


    """Return XML tree representation of the state of the ledger object.

    :returns: XML tree.
    :rtype: lxml.etree.ElementTree
    """
    def to_tree(self):
        return self.tree


    """
    """
    def truncate(self, modify_tree=True):
        self.base = self.cur
        self.serial_base = self.serial

        if not modify_tree:
            return

        inc_tree = self.tree.find('incoming', namespaces=nsmap())
        # xpath does not support empty namespace names
        ns = {'ns': nsmap()[None]}
        for k in self.running:
            o = inc_tree.xpath("ns:real[@unit='{}']".format(k), namespaces=ns)
            v = o[0].find('asset', namespaces=nsmap())
            logg.debug('setting asset {} for {}'.format(self.running[k].asset, k))
            v.text = str(self.running[k].asset)
            v = o[0].find('liability', namespaces=nsmap())
            v.text = str(self.running[k].liability)

        self.reset()

    """Verify digest chain and signatures in ledger.

    :todo: implement, currently a no-op
    """
    def check(self):
        return self


    """Return a string representation of the XML tree.

    :returns: XML document in UTF-8 format.
    :rtype: str
    """
    def to_string(self):
        return lxml.etree.tostring(self.tree)


    """Returns the digest of the current state of the ledger.

    The digest is calculated on the full chain of entries currently in the ledger.

    The digest type is defined in the usawa.Entry.digest_algo.

    :returns: Digest.
    :rtype: bytes 
    """
    def current(self):
        return self.cur


    """Generate the serialization format used to calculate the digest for the entry.

    :returns: String representation of the entry, in rencode format.
    :rtype: str
    """
    def serialize(self):
        ts = int(self.dt.timestamp())
        ts_bytes = ts.to_bytes(4, byteorder='big')
        units = self.uidx.serialize()
        identities = self.acl.serialize()
        totals = []
        v = self.running[self.uidx.base].serialize()
        totals.append(v)
        for k in self.running.keys():
            if k == self.uidx.base:
                continue
            v = self.running[k].serialize()
            totals.append(v)
        d = [
                self.topic,
                varints.leb128s.encode(self.serial),
                self.cur,
                ts_bytes,
                units, 
                identities,
                totals,
                ]
        logg.debug('serialize ledger {}'.format(d))
        return rencode.dumps(d)


    """

    :raises AttributeError: Ledger is missing wallet
    """
    def sign(self):
        if self.wallet == None:
            raise AttributeError()
        v = self.serialize()
        r = self.wallet.sign(v)
        k = self.wallet.pubkey()
        self.add_signature(r, k)
        return r



    """Create a ledger object from serialized data.

    :param data: rencoded ledger object, as produced by the serialize() method.
    :type data: str
    :returns: Ledger object.
    :rtype: usawa.Ledger
    """
    @staticmethod
    def deserialize(self, unitindex, serial=None, base=None, acl=None, src=None):
        v = rencode.loads(data)
        o = Ledger(base=base, serial=serial, acl=acl, src=src, topic=v[0])
        return o


    def __str__(self):
        return "state: " + self.base.hex()
