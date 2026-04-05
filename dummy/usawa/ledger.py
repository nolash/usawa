import enum
import os
import datetime

import logging
import hashlib

import lxml.etree
import rencode
import varints.leb128s

from .base import UsawaElement
from .crypto import DemoWallet, ACL
from .xml import nsmap, XML_FORMAT_VERSION
from .constant import NSPREFIX, DEFAULTPARENT
from .entry import Entry
from .unit import UnitIndex
from .util import to_datestring
from .error import VerifyError

logg = logging.getLogger('usawa.ledger')


class CallbackType(enum.Enum):
    PRE = 'PRE'
    POST = 'POST'


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
        self.real = False



    """Mark the running total as representing a "real" (non-derivative) asset.

    :seealso: to_tree()
    """
    def set_real(self):
        self.real = True


    """Return the current asset/liability balance.

    :return: Balance
    :rtype: int
    """
    def get_balance(self):
        return self.asset - self.liability 

    """Return the current income/expense result.

    :return: Result. 
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
        fn = getattr(self, typ.lower() + '_delta')
        fn(amount)


    """Instantiate a Running total object from XML.

    The expected XML is the Balance complex type; ledger/incoming/real or ledger/incoming/virt.

    :param tree: XML tree
    :type tree: lxml.etree.Element
    :return: Unit index
    :rtype: usawa.UnitIndex
    """
    @staticmethod
    def from_tree(tree, unitindex):
        unit = tree.get('unit')
        asset = int(tree.find('asset', namespaces=nsmap()).text)
        liability = int(tree.find('liability', namespaces=nsmap()).text)
        income = int(tree.find('income', namespaces=nsmap()).text)
        expense = int(tree.find('expense', namespaces=nsmap()).text)
        return RunningTotal(unit, unitindex, asset=int(asset), liability=int(liability), income=int(income), expense=int(expense))



    """Generate an XML tree from the current state of the object.

    The XML generated can be used as a "real" or "virt" sub-element of the ledger/incoming/ element.

    By default, a "virt" tag will be used, unless set_real() has been previously called.

    :return: XML tree
    :rtype: lxml.etree.Element
    """
    def to_tree(self):
        tag = 'virt'
        if self.real:
            tag = 'real'
        tree = lxml.etree.XML('<{}></{}>'.format(tag, tag))
        tree.set('unit', self.sym)
        o = lxml.etree.SubElement(tree, 'income')
        o.text = str(self.income)
        tree.append(o)

        o = lxml.etree.SubElement(tree, 'expense')
        o.text = str(self.expense)
        tree.append(o)
        
        o = lxml.etree.SubElement(tree, 'asset')
        o.text = str(self.asset)
        tree.append(o)

        o = lxml.etree.SubElement(tree, 'liability')
        o.text = str(self.liability)
        tree.append(o)
        
        return tree


    """Generate the simple data structure used for rencode serialization.

    :returns: data structure
    :rtype: list
    """
    def to_list(self):
        d = [
                self.sym,
                varints.leb128s.encode(self.income),
                varints.leb128s.encode(self.expense),
                varints.leb128s.encode(self.asset),
                varints.leb128s.encode(self.liability),
                ]
        return d


    """Generate the unit index part of an Entry in wire format.

    :return: rencoded object
    :rtype: bytes
    """
    def serialize(self):
        d = self.to_list()
        return rencode.dumps(d)


    def __str__(self):
        return 'running total {}: income {} expense {} asset {} liability {}'.format(self.sym, self.income, self.expense, self.asset, self.liability)


class Ledger(UsawaElement):

    default_src = 'defalsify.org'

    """Ledger represents a signed and verified chain of transaction entries.

    Apart from the entries chain, it also holds metadata required to expand underlying assets referenced by the entries, aswell as resolution and verification of identities of signatories.

    If populated by an XML tree, all unit definitions encountered will be added to the provided UnitIndex. All other parameters will be ignored.

    If the serial number parameter is non-zero, the base must be a non-zero digest value.

    The src parameter is not the same as resolved. Whereas the resolver is used to retrieve assets from a content-addressed storage, the src rather points to a context rich resource containing ledger and entry data intended for human consumption.

    :param unitindex: The unit index to resolve transaction values used in the entries.
    :type unitindex: usawa.UnitIndex
    :param acl: A collection of public keys to use to verify signatures. Will override existing public key lists.
    :type acl: usawa.ACL
    :param serial: Serial number to start the current state of the ledger on.
    :type serial: int
    :param base: Hexadecimal digest value defining the state of the ledger at the corresponding serial number. The digest type is defined in usawa.Entry.digest_algo
    :type base: str
    :param topic: Hexadecimal userdata providing context of the ledger.
    :type topic: str
    :param src: URI for the source of the data contained by the legder.
    :type src: str
    :param wallet: Wallet to use to sign the ledger state for XML exports.
    :type wallet: usawa.Wallet
    :todo: Add warnings for ignored parameters
    :todo: Remove enclosing array for entries
    """
    def __init__(self, unitindex, acl=None, serial=0, base=DEFAULTPARENT, topic=None, src=None, wallet=None):
        self.uidx = unitindex
        self.sigs = {}
        self.entries = {}
        self.running = {}
        self.wallet = None
        self.lookup = None
        self.lookup_algo = 'sha512'
        self.pre_cb = []
        self.post_cb = []

        for k in self.uidx.syms():
            if self.running.get(k) != None:
                continue
            logg.debug('add new runningtotal for {}'.format(k))
            self.running[k] = RunningTotal(k, self.uidx)
            if self.uidx.base == k:
                self.running[k].set_real()
        self.resolvers = {}
        
        self.base = base
        self.base_serial = serial
        self.src = src
        self.topic = topic
        self.acl = acl
        self.dt = datetime.datetime.utcnow()
        if wallet != None:
            self.set_wallet(wallet)
        if self.topic == None:
            self.topic = os.urandom(64)
        if base == None:
            h = hashlib.sha512()
            h.update(topic)
            h.update(DEFAULTPARENT)
            base = h.digest()
        
        self.serial = self.base_serial
        self.cur = base
        logg.debug('ledger base {} serial {} from topic {}'.format(self.base.hex(), self.serial, self.topic.hex()))


    """Wallet to use to sign ledger for XML exports.

    :param v: Wallet to set
    :type v: usawa.Wallet
    :todo: Verify that this does not inadvertently affect the ACL
    """
    def set_wallet(self, v):
        self.wallet = v
        pubkey = self.wallet.pubkey()
        if self.acl == None:
            self.acl = ACL.from_wallet(self.wallet)
        elif not self.acl.have(pubkey):
            self.acl.add(pubkey)

        try:
            self.sigs[pubkey]
            return
        except KeyError:
            pass
        self.sigs[pubkey] = b''


    """Add callback to be invoked for each entry added to the ledger.

    Callback will be passed entry as the sole argument.

    :param fn: Callback function
    :type fn: function
    """
    def register_callback(self, fn, typ=CallbackType.POST):
        if typ == CallbackType.PRE:
            self.pre_cb.append(fn)
        elif typ == CallbackType.POST:
            self.post_cb.append(fn)
        else:
            raise ValueError('invalid callback type')


    """Retrieve the serial that will be assigned to the next entry, without incrementing it in the object state.

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


    """Generate a ledger XML tree from the current state of the ledger.

    It includes XML for all subordinate objects necessary to build a document that can be validated by the XML schema.

    This method will also generate XML entries for all entries in the object state. If only the current ledger state is desired, a preceding call to truncate() is needed.

    :return: XML tree of ledger
    :rtype: lxml.etree.Element
    :todo: split up function
    :todo: implement XML identity export for wallet
    :todo: enable use of multiple "real" elements
    :todo: deduplicate signature from wallet identity if already exists
    """
    def to_tree(self, lookup=None):
        #self.serial = self.base_serial
        #self.cur = self.base
        tree = lxml.etree.XML('<ledger xmlns="http://usawa.defalsify.org/" version="{}"></ledger>'.format(XML_FORMAT_VERSION))

        # generate topic
        o = lxml.etree.Element('topic')
        tree.append(o)
        if self.topic == None:
            topic = os.urandom(64)
            topic = topic.hex()
        else:
            topic = self.topic.hex()
        o.text = topic

        # datetime (this) ledger snapshot generated
        o = lxml.etree.SubElement(tree, 'generated')
        self.dt = datetime.datetime.now()
        o.text = to_datestring(self.dt)

        # the human-readable source for ledger data
        o = lxml.etree.SubElement(tree, 'src')
        if self.src == None:
            src = self.default_src
        else:
            src = self.src
        o.text = src

        # unit index
        units_tree = self.uidx.to_tree()
        tree.append(units_tree)
       
        # identity entry for the key signing the ledger state.
        if self.wallet != None:
            o = self.wallet.to_tree()
            tree.append(o)
        
        # incoming state
        incoming = lxml.etree.SubElement(tree, 'incoming')

        # incoming serial
        incoming.set('serial', str(self.base_serial))

        # incoming base (real) currency balance
        o = self.running[self.uidx.base].to_tree()
        incoming.append(o)

        # incoming remaining (virt) currency balances
        for k in self.running.keys():
            if k == self.uidx.base:
                continue
            o = self.running[k].to_tree()
            incoming.append(o)

        # incoming entry digest
        o = lxml.etree.SubElement(incoming, 'digest')
        o.attrib['algo'] = 'sha512'
        o.text = self.base.hex()
        incoming.append(o)

        if self.lookup != None:
            o = lxml.etree.SubElement(incoming, 'lookup')
            o.attrib['algo'] = self.lookup_algo
            o.text = self.lookup
            incoming.append(o)

        # incoming signatures
        # sign the ledger if it has no signatures
        if len(self.sigs.keys()) == 0:
            self.sign()

        # apply all already existing signatures (e.g. from import)
        for k in self.sigs.keys():
            sig = self.sigs[k]
            if len(sig) == 0:
                continue
            o = lxml.etree.SubElement(incoming, 'sig')
            o.set('keyid', k.hex())
            o.set('type', 'ed25519')
            o.text = sig.hex()
            incoming.append(o)

        # apply all entries in object state
        for k in self.entries.keys():
            v = self.entries[k]
            entry_tree = v.to_tree(lookup=lookup)
            tree.append(entry_tree)

        return tree


    """Check signature on individual ledger entry.

    :param entry: The individual entry to verify.
    :type entry: usawa.Entry
    :raises usawa.VerifyError: No valid signatures found.
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
            if sig == None:
                raise ValueError('Signature entry without signature value')
            wallet = DemoWallet(publickey=b)
            v = entry.sum()
            return wallet.verify(v[0], sig)
            have = True
        if not have:
            raise VerifyError()


    """Append entry to ledger. The entry must have a valid signature from a trusted public key.

    Any entry added here will be part of the XML export, unless truncate() is called afterwards.

    :param entry: The entry to append.
    :type entry: usawa.Entry
    :raises ValueError: When entry parent does not match ledger state.
    :raises VerifyError: When entry is missing valid signature.
    """
    def add_entry(self, entry, check_parent=True):
        parent = entry.parent.hex()
        if check_parent and self.cur != entry.parent:
            raise ValueError('entry parent {} does not match ledger state {}'.format(parent, self.cur.hex()))
        self.check_sigs(entry)
        logg.debug('entry state ok: ' + parent)

        for fn in self.pre_cb:
            if not fn(entry):
                raise VerifyError('entry pre callback not passed')

        # update the internal state
        self.serial = entry.serial
        #oldsum = self.cur
        #self.cur = entry.sum()[0]
        (k, v) = entry.get_lookup(self.lookup_algo)
        logg.debug('addentr entry for algo {}: {} {}'.format(self.lookup_algo, k, v))
        #entry.parent = oldsum
        # TODO: parent being changed after sealed and signed, why?
        entry.parent = self.cur
        self.cur = bytes.fromhex(k)
        logg.debug('selfcur is now {}'.format(self.cur.hex()))
        self.apply_entryparts(entry)

        # Add entry to the ledger object.
        self.entries[entry.serial] = entry

        for fn in self.post_cb:
            if not fn(entry):
                raise VerifyError('entry post callback not passed')


    """Update running total according to the entry.

    Object does not keep track of which entries have been applied to the running total. Caller must take care not to call this more than once for each entry.

    :param entry: Entry whose parts to apply to running total.
    :type entry: usawa.Entry
    """
    def apply_entryparts(self, entry):
        for v in entry.debit:
            amount = v.amount
            #if v.isdebit:
            #    amount *= -1
            self.running[v.unit].apply(v.typ, amount)

        for v in entry.credit:
            amount = v.amount
            #if v.isdebit:
            #    amount *= -1
            self.running[v.unit].apply(v.typ, amount)

        logg.debug('applied entry {} src {} dst {}'.format(entry.serial, entry.debit, entry.credit))


    """Add a signature on the ledger.
    
    :todo: not an appropriate API function?
    :todo: implement validity checks for signature.
    :todo: canonlicalize identity
    """
    def add_signature(self, sigdata, identity):
        self.sigs[identity] = sigdata
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
    def from_tree(tree, acl=None):
        topic_node = tree.find('topic', namespaces=nsmap())
        topic = bytes.fromhex(topic_node.text)

        units = tree.find('units', namespaces=nsmap())
        unitindex = UnitIndex.from_tree(units)

        unit = units.get('base')
        part = tree.find('incoming', namespaces=nsmap())
        serial = int(part.get('serial'))
        
        o = part.find('digest', namespaces=nsmap()).text # verify that is sha512
       
        ledger = Ledger(unitindex, topic=topic, acl=acl, serial=serial, base=bytes.fromhex(o))

        for sig in part.findall('sig', namespaces=nsmap()):
            keyid = sig.get('keyid')
            digest = sig.text
            ledger.add_signature(bytes.fromhex(digest), bytes.fromhex(keyid))

        for identity in tree.findall('identity', namespaces=nsmap()):
            keyid = identity.get('keyid')
            didtyp = identity.get('didtype')
            did = identity.text
            public_key = bytes.fromhex(keyid)
            wallet = DemoWallet(publickey=public_key)
            ledger.set_wallet(wallet)
            logg.warning('currently only support for single identity')
            break

        for v in part.iter(NSPREFIX + 'real'):
            sym = v.get('unit')
            o = RunningTotal.from_tree(v, unitindex)
            ledger.running[o.sym] = o
            logg.debug('ledger running total {} (real): {}'.format(o.sym, o))

        for v in part.iter(NSPREFIX + 'virt'):
            sym = v.get('unit')
            o = RunningTotal.from_tree(v, unitindex)
            ledger.running[o.sym] = o
            logg.debug('ledger running total {} (virt): {}'.format(o.sym, o))

        if ledger.running.get(unit) == None:
            ledger.running[unit] = RunningTotal(unit, unitindex)

        o = part.find('lookup', namespaces=nsmap())
        if o != None:
            ledger.lookup = o.text
            ledger.lookup_algo = o.get('algo')

        ledger.apply_entries(tree)
        logg.debug('loaded ledger tree last serial {}'.format(ledger.serial))

        return ledger.check()


    @staticmethod
    def from_file(filepath, acl=None):
        f = open(filepath, 'rb')
        v = f.read()
        f.close()
        return Ledger.from_string(v, acl=acl)



    """Append all entries from XML tree to ledger.

    :param tree: A parsed XML tree.
    :todo: Not an API method.
    """
    def apply_entries(self, tree):
        start = self.serial
        last = 1
        i = 0
        for v in tree.iter(NSPREFIX + 'entry'):
            i += 1
            o = Entry.from_tree(v, self.uidx, min=self.serial)
            self.add_entry(o)
            (k, v) = o.get_lookup('sha512')
            if o.serial > last:
                last = o.serial
            #self.cur = k
        if i > 0:
            self.serial = last
        logg.info('last entry from tree serial ' + str(self.serial))


    def last_entry(self):
        serial = -1
        digest = None
        for i in self.entries.keys():
            if i > serial:
                serial = i
        return self.entries[serial]


    """Calculate and apply ledger state from current entries in the object, and remove entries.

    After this call, the XML export will not contain any entry elements, and will have digest and serial from the last entry that existed in the ledger.
    """
    def truncate(self, lookup=None):
        self.base = self.cur
        self.base_serial = self.serial
        logg.debug('base serial now {}'.format(self.base_serial))
        try:
            entry = self.last_entry()
        except KeyError: # if no entries
            self.entries = {}
            return
        if lookup != None:
            (k, v) = entry.get_lookup(lookup)
            logg.debug('trunc looup {} {}'.format(k, v))
            self.lookup = k
            self.lookup_algo = lookup
        self.entries = {}


    """Verify digest chain and signatures in ledger.

    :todo: implement, currently a no-op
    """
    def check(self):
        return self


    """Return a string representation of the XML tree.

    :return: XML document in UTF-8 format.
    :rtype: str
    """
    def to_string(self, lookup=None):
        tree = self.to_tree(lookup=lookup)
        return lxml.etree.tostring(tree).decode('utf-8')

    
    @staticmethod
    def from_string(s, acl=None):
        tree = lxml.etree.fromstring(s)
        return Ledger.from_tree(tree, acl=acl)


    """Returns the digest of the current state of the ledger.

    The digest is calculated on the full chain of entries currently in the ledger.

    The digest type is defined in the usawa.Entry.digest_algo.

    :return: Digest.
    :rtype: bytes 
    """
    def current(self):
        return self.cur


    """Returns the serial of the latest entry added to the ledger.

    :return: Serial.
    :rtype: int
    """
    def current_serial(self):
        return self.serial


    """Generate canonical XML for signature material.

    :return: Signature material.
    :rtype: str
    """
    def canon(self):
        tree = self.to_tree(lookup=False)
        b = lxml.etree.canonicalize(tree, strip_text=True, exclude_tags=['sig'])
        return b.encode('utf-8')


    """Sign the ledger with the assigned wallet.

    The wallet must have been passed in the wallet attribute during instantiation, or using set_wallet() preceding this call.

    Any existing signature for the same object will be overwritten.

    :raises AttributeError: Ledger is missing wallet
    :returns: Signature data
    :rtype: bytes
    """
    def sign(self):
        if self.wallet == None:
            raise AttributeError()
        #v = self.serialize()
        v = self.canon()
        r = self.wallet.sign(v)
        k = self.wallet.pubkey()
        self.add_signature(r, k)
        return r


    def __str__(self):
        return "state: " + self.base.hex() + " serial " + str(self.serial)
