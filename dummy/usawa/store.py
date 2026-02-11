import enum
import os
import logging

from whee import Interface

from .ledger import Ledger
from .entry import Entry


PFX_KEY = b'\x00'
PFX_LEDGER = b'\x01'
PFX_LEDGER_LOCK = b'\x02'
PFX_ENTRY = b'\x04'

logg = logging.getLogger('usawa.store')


"""DB key prefix for a private key entry

If public key is not specified, the prefix will reference the DEFAULT key.

:param pubkey: Public key to get private key for.
:type pubkey: bytes
:return: DB prefix
:rtype: bytes
"""
def pfx_key(pubkey=None):
    v = PFX_KEY
    if pubkey == None:
        return v
    return v + pubkey


"""DB key prefix for the ledger state of a topic.

:param topic: Legder topic.
:type topic: bytes
:return: DB prefix
:rtype: bytes
"""
def pfx_ledger_topic(topic):
    """Return ledger store prefix for topic.

    :params topic: Topic to generate prefix for.
    :type topic: bytes
    :returns: Prefix.
    :rtype: bytes
    """
    r = PFX_LEDGER + topic
    return r


"""DB key prefix for locking the ledger state of a topic.

:param topic: Legder topic.
:type topic: bytes
:return: DB prefix
:rtype: bytes
"""
def pfx_ledger_lock(topic):
    """Return ledger store locking prefix for topic.

    :params topic: Topic to generate prefix for.
    :type topic: bytes
    :returns: Prefix.
    :rtype: bytes
    """
    r = PFX_LEDGER_LOCK + topic
    return r


"""DB key prefix for adding an entry to a ledger.

:param ledger: Ledger object.
:type ledger: usawa.Ledger
:param entry: Entry object to add to ledger.
:type entry: usawa.Entry
:return: DB prefix
:rtype: bytes
"""
def pfx_entry(ledger, entry):
    """Return ledger store prefix for an entry.

    :param ledger: Ledger context for the entry.
    :type ledger: usawa.Ledger
    :param entry: Entry or serial to create prefix for.
    :type entry: usawa.Entry or int
    :returns: Prefix.
    :rtype: bytes
    """
    serial = 0
    if isinstance(entry, Entry):
        serial = entry.serial
    elif isinstance(entry, int):
        serial = entry
    else:
        raise ValueError('invalid entry')
    if not isinstance(ledger, Ledger):
        raise ValueError('invalid ledger')
    return PFX_LEDGER + ledger.topic + serial.to_bytes(8, byteorder='big')


class LedgerStore(Interface):
    """Wrapper for an implementation of the whee store that handles encoding of ledgers and entries.

    :param implementation: Store implementation.
    :type implementation: whee.Interface (implementation)
    :param ledger: The ledger for which to execute store operations.
    :type ledger: usawa.Ledger
    """
    def __init__(self, implementation, ledger):
        if not isinstance(implementation, Interface):
            raise ValueError('store must be whee interface instance')
        if not isinstance(ledger, Ledger):
            raise ValueError('invalid ledger')
        self.ledger = ledger
        self.__o = implementation


    """Implements whee.Interface.start
    """
    def start(self):
        serial = 0
        k = pfx_ledger_topic(self.ledger.topic)
        try:
            b = self.__o.get(k)
            serial = int.from_bytes(8, byteorder='big')
        except FileNotFoundError:
            v = serial.to_bytes(8, byteorder='big')
            self.__o.put(k, v)
        self.ledger.serial = serial


    """Implements whee.Interface.lock
    """
    def lock(self):
        k = pfx_ledger_lock(self.ledger.topic)
        v = None
        # TODO: needs to be an atomic routine
        try:
            v = self.__o.get(k)
        except KeyError:
            raise PermissionError()
        self.__o.put(k, 0x01, exist_ok)
        # atomic until here


    """Implements whee.Interface.unlock
    """
    def unlock(self):
        k = pfx_ledger_lock(self.ledger.topic)
        v = self.__o.delete(k)


    """Add an entry to the store.

    :param entry: Entry to add.
    :type entry: usawa.Entry or int
    :param update_ledger: Add the underlying ledger object with the entry.
    :type update_ledger: boolean
    :raises: ValueError if the entry is not the right object type.
    :raises: FileExistsError if entry is already in store.
    """
    def add_entry(self, entry, update_ledger=False):
        k = pfx_entry(self.ledger, entry)
        v = entry.wrap()
        self.__o.put(k, v)
        if update_ledger:
            self.ledger.add_entry(entry)


    """Restore an entry from data from the store.

    The entry is referenced by its serial number within the store's ledger. It can either be specified as an integer, or an entry object with the serial number property set accordingly.

    :param entry: Entry of entry serial to restore.
    :type entry: usawa.Entry or int
    :param acl: Optional collection of public keys to validate signatures against.
    :type acl: usawa.ACL
    :raises: PermissionError if the entry does not have a valid signature.
    :raises: ValueError if the serial number cannot be retrieved from the entry argument.
    :raises: FileExistsError if entry is already in store.
    """
    def get_entry(self, entry, acl=None):
        k = pfx_entry(self.ledger, entry)
        v = self.__o.get(k)
        return Entry.unwrap(v, acl=acl)


    """Flush ledger and load all entries from store.

    The existing state will always be lost.

    If the load fails, the ledger will be reset before returning.

    :raises FileNotFoundError: If an entry cannot be found.
    """
    def load(self):
        logg.debug('load ledger from store {}'.format(self.ledger))
        while True:
            o = None
            try:
                o = self.get_entry(self.ledger.next_serial())
            except FileNotFoundError:
                break
            self.ledger.add_entry(o)


    """Add signing key to the store.

    If this is the first key in the store, it will be set as default.

    :param wallet: The wallet object to store keys for.
    :type wallet: usawa.Wallet implementation
    :param default: If True, this key will be set as default key.
    :type default: bool
    :todo: Currently the signing key is stored literally. It needs encryption!
    """
    def add_key(self, wallet, default=False):
        k = pfx_key()
        try:
            self.__o.get(k)
        except FileNotFoundError:
            default = True
        pubkey = wallet.pubkey()
        if default:
            self.__o.put(k, pubkey, exist_ok=True)
        k = pfx_key(pubkey=pubkey)
        self.__o.put(k, wallet.privkey())


    """Get corresponding private key from the store.
    
    If public key is not supplied, will retrieve the default private key.

    :param pubkey: Public key to retrieve private key for.
    :type pubkey: bytes
    :return: Resulting key
    :rtype: bytes
    """
    def get_key(self, pubkey=None):
        if pubkey == None:
            k = pfx_key()
            pubkey = self.__o.get(k)
        k = pfx_key(pubkey=pubkey)
        return self.__o.get(k)


    def put(self, k, v):
        return self.__o.put(k, v)


    def get(self, k):
        return self.__o.get(k)
