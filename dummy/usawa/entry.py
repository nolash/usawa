import enum
import logging
import datetime
import uuid
import hashlib

import lxml.etree
import rencode

from .constant import DEFAULTPARENT, NSPREFIX
from .crypto import DemoWallet
from .error import ACLError, VerifyError
from .xml import nsmap

logg = logging.getLogger('usawa.entry')


class KeyStoreFormat(enum.IntEnum):
    """
    :todo: Unclear what purpose this serves, only literal in use now.
    """
    LITERAL = 0
    INDEXED = 1


class EntryPart:
    """EntryPart is a single part of transaction, representing either side of a double-accounting ledger.

    Each side of the transaction may have several parts.

    :param unit: Unit of account of transaction part.
    :type unit: str
    :param typ: One of 'asset', 'liability', 'income', 'expense'
    :type typ: str
    :param account: A path-like account name.
    :type account: str
    :param amount: Amount as integer, including decimals according to unit precision.
    :type amount: int
    :param debit: True if the transaction part is a debit.
    :type debit: boolean
    :todo: Make typ enum
    """
    def __init__(self, unit, typ, account, amount, debit=False):
        self.unit = unit
        self.typ = typ
        self.account = account
        self.amount = amount
        self.isdebit = debit


    """Create object from an entry part defined as an XML tree.

    The XML expected is the ledger/entry/data/debit or ledger/entry/data/credit (in schema, defined as the EntryPart complexType).

    :param tree: The entry as XML tree.
    :type tree: lxml.etree.ElementTree
    :param debit: True if the transaction part is a debit.
    :type debit: boolean
    :return: Entry part
    :rtype: usawa.EntryPart
    """
    @staticmethod
    def from_tree(tree, debit=False):
        typ = tree.get('type')
        unit = tree.find('unit', namespaces=nsmap()).text
        amount = int(tree.find('amount', namespaces=nsmap()).text)
        account = tree.find('account', namespaces=nsmap()).text
        return EntryPart(unit, typ, account, amount, debit=debit)


    """Generate XML element from state of entry part.

    The XML generated is valid for insertion as ledger/entry/data as elements debit and credit.

    :returns: XML tree.
    :rtype: lxml.etree.Element
    :todo: Not an API function?
    """
    def to_tree(self):
        tag = 'credit'
        if self.isdebit:
            tag = 'debit'

        tree = lxml.etree.Element(tag, type=self.typ, nsmap=nsmap())

        o = lxml.etree.Element('unit')
        o.text = self.unit
        tree.append(o)

        o = lxml.etree.Element('account')
        o.text = self.account
        tree.append(o)

        o = lxml.etree.Element('amount')
        o.text = str(self.amount)
        logg.debug('tree amount {} {}'.format(self.unit, o.text))
        tree.append(o)

        return tree


    def __str__(self):
        pfx = 'credit'
        if self.isdebit:
            pfx = 'debit'
        return '[{}] {}:{} {}'.format(pfx, self.typ, self.account, self.amount)


class Entry:

    digest_algo = 'sha512' # The algorithm used for generating entry digests. Must match a hashlib (standard library) type string identifier.

    """Entry represents a single pair of accounts, credit and debit, for a transaction.

    If parent is not specified, the entry will be expected to be the first entry in the ledger, and the serial number must be zero.

    If unitindex is not specified, unit symbols in entry parts will not be validated as they are added.

    :param serial: The entry's serial number in the ledger.
    :type serial: int
    :param tx_date: The date of the transaction.
    :type tx_date: datetime.date
    :param ref: A unique reference UUID for the transation. If not specified, one will be automatically generated.
    :type ref: uuid.UUID
    :param description: An optional textual description of the transaction.
    :type description: str
    :param parent: Digest of the preceding ledger state, in hexadecimal format.
    :type parent: str
    :param tx_datereg: Date and time entry was added to the ledger. If not set, the current date and time will be used.
    :type tx_datereg: datetime.datetime
    :param unitindex: Unix index top validate unit symbols and exchange rates against.
    :type unitindex: UnitIndex
    :todo: Add an optional time part to the entry, e.g. for POS items.
    :todo: Implement throw error if non-zero serial has zero-value digest.
    :todo: Check hashlen of parent against actual digest length defined in digest_algo.
    :todo: Prevent changes after the first signature calculation.
    :todo: Ensure canonical format of keyid.
    """
    def __init__(self, serial, tx_date, ref=None, description=None, parent=None, tx_datereg=None, unitindex=None):
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
        self.serial = serial
        self.dt = tx_date
        self.uidx = unitindex
        if tx_datereg == None:
            tx_datereg = datetime.datetime.now()
        self.dtreg = tx_datereg
        self.attachment = []
        self.sigs = {}
        self.description = description
        self.debit = []
        self.credit = []


    """Add an entry part to the entry.

    At least one debit and one credit item must be added to be valid.

    :param part: Entry part to add
    :type part: EntryPart
    :param debit: If true, entry part will be added to debits. If false, credits.
    :type debit: boolean
    :raises KeyError: Symbol does not exist in unit index.
    """
    def add_part(self, part, debit=False):
        if self.uidx != None:
            self.uidx.sym(part.unit)
        if debit:
            self.debit.append(part)
        else:
            self.credit.append(part)


    """Append a single media asset to the attachment list for the entry.

    :param mime: MIME type of asset.
    :type mime: str
    :param algo: Algorithm used to generate digest of attachment. Must be a valid algorithm identifier for hashlib (standard library).
    :type algo: str
    :param digest: The digest of the asset.
    :type digest: bytes
    :param description: Optional description string for the asset.
    :type description: str
    :param slug: Optional machine-friendly name, e.g. used as filename stem.
    :type slug: str
    """
    def attach(self, mime, algo, digest, description=None, slug=None):
        self.attachment.append((mime, algo, digest, description, slug,))


    """Add a signature over the ledger state of the entry.

    :param keyid: Key identifier, e.g. as used in a DID.
    :type keyid: str or bytes
    :param sigdata: Key identifier, e.g. as used in a DID.
    :type sigdata: bytes
    """
    def add_signature(self, keyid, sigdata):
        if isinstance(keyid, bytes):
            keyid = keyid.hex()
        self.sigs[keyid] = sigdata


    """Create an entry object from an XML representation.

    :param tree: A parsed XML tree containing the entry.
    :type tree: lxml.etree.ElementTree
    :param unitindex: A unitindex containing the necessary definitions for the unit symbol used in the entry.
    :type unitindex: usawa.UnitIndex
    :param min: Minimal valid serial entry.
    :type min: int
    :raises ValueError: serial is less than min
    :returns: Entry object.
    :rtype: usawa.Entry
    """
    @staticmethod
    def from_tree(tree, unitindex, min=0):
        o = tree.find('data', namespaces=nsmap())
        serial = int(o.find('serial', namespaces=nsmap()).text)
        if min > serial:
            raise ValueError('entry serial preceeds ledger')
        #unit = o.find('unit', namespaces=nsmap()).text
        #unitindex.sym(unit)

        ref = o.find('ref', namespaces=nsmap()).text
        parent = o.find('parent', namespaces=nsmap()).text
        description = o.find('description', namespaces=nsmap())
        if description != None:
            description = description.text
        dt = datetime.date.fromisoformat(o.find('date', namespaces=nsmap()).text)
        dtreg = datetime.datetime.strptime(o.find('dateTimeRegistered', namespaces=nsmap()).text, '%Y-%m-%dT%H:%M:%SZ')
    
        src_tree = o.find('debit', namespaces=nsmap())
        dst_tree = o.find('credit', namespaces=nsmap())

        o = Entry(serial, dt, ref=ref, parent=parent, tx_datereg=dtreg, description=description, unitindex=unitindex)

        src = EntryPart.from_tree(src_tree, debit=True)
        dst = EntryPart.from_tree(dst_tree)
        o.add_part(src, debit=True)
        o.add_part(dst)

        for sig in tree.iter(NSPREFIX + 'sig'):
            o.add_signature(sig.get('keyid'), bytes.fromhex(sig.text))

        return o

    """Generate the simple data structure used for rencode serialization.

    :returns: data structure
    :rtype: list
    """
    def to_list(self):
        debit = []
        credit = []
        for v in self.debit:
            debit.append((v.unit, v.typ, v.account, v.amount,))

        for v in self.credit:
            credit.append((v.unit, v.typ, v.account, v.amount,))

        d = [
                self.parent,
                self.serial,
                self.ref,
                self.dtreg.strftime('%Y%m%d%H%M%S'),
                self.dt.strftime('%Y%m%d'),
                self.description,
                debit,
                credit,
                ]
        return d


    """Generate the serialization format used to calculate the digest for the entry.

    :returns: String representation of the entry, in rencode format.
    :rtype: str
    """
    def serialize(self):
        b = self.to_list()
        return rencode.dumps(b)


    """Create an entry object from serialized data.

    :param data: rencoded entry object, as produced by the serialize() method.
    :type data: str
    :returns: Entry object.
    :rtype: usawa.Entry
    """
    @staticmethod
    def deserialize(data):
        v = rencode.loads(data)
        parent = v[0].hex()
        serial = v[1]
        ref = v[2].decode('utf-8')
        date_reg = datetime.datetime.strptime(v[3].decode('utf-8'), '%Y%m%d%H%M%S')
        date = datetime.datetime.strptime(v[4].decode('utf-8'), '%Y%m%d')
        #unit = v[5].decode('utf-8')
        description = v[5].decode('utf-8')
        src_data = v[6]
        dst_data = v[7]
        o = Entry(serial, date, ref=ref, description=description, parent=parent, tx_datereg=date_reg)
        for v in src_data:
            src = EntryPart(v[0].decode('utf-8'), v[1].decode('utf-8'), v[2].decode('utf-8'), v[3], debit=True)
            o.add_part(src, debit=True)

        for v in dst_data:
            dst = EntryPart(v[0].decode('utf-8'), v[1].decode('utf-8'), v[2].decode('utf-8'), v[3])
            o.add_part(dst)
        logg.debug('deserialized entry {}'.format(o))
        
        return o


    """Calculate and return the digest of the entry.

    :returns: Tuple with two members, containing the digest of entry and the serialized data, respectively.
    :rtype: tuple
    """
    def sum(self):
        b = self.canon()
        h = hashlib.new(self.digest_algo)
        h.update(b)
        return (h.digest(), b)


    """Add a signature to the entry.

    The digest of the entry is automatically generated from the current state of the entry.

    :param wallet: Wallet containing private key used to sign the entry.
    :type wallet: usawa.Wallet
    :returns: Tuple with three members, containing the digest of entry, the signature, and the serialized data, respectively.
    :rtype: tuple
    """
    def sign(self, wallet):
        (z, b) = self.sum()
        r = wallet.sign(z)
        pubk_hx = wallet.pubkey().hex()
        self.sigs[pubk_hx] = r
        logg.debug('added signature from key {}'.format(pubk_hx))
        return (z, r, b,)


    """Bundle signed, serialized entry data with public keys used to sign the entry.

    :param wallet: If defined, add a signature from the given wallet to the entry.
    :type wallet: usawa.Wallet
    :todo: Current specifying wallet has no effect.
    """
    def wrap(self, wallet=None):
        digest = None
        data = None
        if wallet != None:
            (digest, _sig, _data) = self.sign(wallet)
            data = self.serialize()
        elif len(self.sigs) == 0:
            raise PermissionError('at least one signature required')
        else:
            (digest, _data) = self.sum()
            data = self.serialize()

        hdr = []
        sigs = []
        for k in self.sigs:
            hdr.append([
                KeyStoreFormat.LITERAL.value,
                bytes.fromhex(k)
                ])
            sigs.append(self.sigs[k])
        
        if len(sigs) == 0:
            raise VerifyError()

        d = [
                hdr,
                sigs,
                data,
            ]

        return rencode.dumps(d)


    """Create an entry object from serialized data containing valid public keys for signing, generated by the wrap() method.

    If ACL is defined, the public keys defined therein will override the public keys ocontained in the wrapped, serialized data.

    :param data: Serialized, wrapped data.
    :type data: bytes
    :param acl: Optional list of public keys to validate signatures against.
    :type acl: usawa.ACL
    :todo: Currently expects one signature, only operates that first signature.
    :raises: usawa.VerifyError if entry data could not be verified with any available public key.
    :returns: The entry object.
    :rtype: usawa.Entry
    :todo: Current version only takes into account single signature
    """
    @staticmethod
    def unwrap(data, acl=None):
        v = rencode.loads(data)
        pubkey_bytes = v[0][0][1]
        if acl != None:
            label = None
            try:
                label = acl.have(pubkey_bytes)
            except KeyError:
                raise ACLError()
            if not acl.may(label, 0x01):
                raise ACLError()
        wallet = DemoWallet(publickey=pubkey_bytes)
        sig = v[1][0]
        entry = Entry.deserialize(v[2])
        entry.add_signature(pubkey_bytes, sig)
        entry.verify(wallet)
        return entry


    def verify(self, wallet):
        (z, b) = self.sum()
        pubkeys = list(self.sigs.keys())
        sig = self.sigs[pubkeys[0]]
        if not wallet.verify(z, sig):
            raise VerifyError()
        # TODO: demo only takes into account single signature


    """Generate and return an XML representation of the entry.

    :todo: Make sure that sigs publickey lookup key is bytes type
    :returns: XML tree representing the entry.
    :rtype: lxml.etree.ElementTree
    """
    def to_tree(self):
        #tree = etree.Element('entry', type=self.typ)
        tree = lxml.etree.Element(NSPREFIX + 'entry', nsmap=nsmap())
        data = lxml.etree.Element('data')

        o = lxml.etree.Element('parent')
        o.text = self.parent.hex()
        data.append(o)

        o = lxml.etree.Element('ref')
        o.text = self.ref
        data.append(o)

        o = lxml.etree.Element('serial')
        o.text = str(self.serial)
        data.append(o)

        o = lxml.etree.Element('date')
        o.text = self.dt.strftime('%Y-%m-%d')
        data.append(o)

        o = lxml.etree.Element('dateTimeRegistered')
        o.text = self.dtreg.strftime('%Y-%m-%dT%H:%M:%SZ')
        data.append(o)
        
        if self.description:
            o = lxml.etree.Element('description')
            o.text = self.description
            data.append(o)

        for v in self.debit:
            o = v.to_tree()
            data.append(o)

        for v in self.credit:
            o = v.to_tree()
            data.append(o)
        
        tree.append(data)

        for k in self.sigs.keys():
            v = k
            if isinstance(v, bytes):
                v = k.hex()
            o = lxml.etree.Element('sig', type='ed25519', keyid=v)
            o.text = self.sigs[k].hex()
            tree.append(o)

        return tree


    """Generate canonical XML for signature material.

    :return: Signature material.
    :rtype: str
    """
    def canon(self):
        tree = self.to_tree()
        b = lxml.etree.canonicalize(tree, strip_text=True, exclude_tags=['sig'])
        return b.encode('utf-8')


    def __str__(self):
        return 'entry serial {} parent {}'.format(self.serial, self.parent.hex())
