import enum
import os
import logging

from whee import Interface

from .ledger import Ledger
from .entry import Entry
from .asset import Asset


PFX_KEY = b'\x00'
PFX_LEDGER = b'\x01'
PFX_LEDGER_INDEX = b'\x02'
PFX_LEDGER_LOCK = b'\x03'
PFX_ENTRY = b'\x04'
PFX_UNIT_INDEX = b'\x08'
PFX_ASSET = b'\x10'

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
    r = PFX_LEDGER + topic
    return r


"""DB key prefix for locking the ledger state of a topic.

:param topic: Legder topic.
:type topic: bytes
:return: DB prefix
:rtype: bytes
"""
def pfx_ledger_lock(topic):
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


"""DB key prefix for adding entry attachment asset to a ledger.

"""
def pfx_asset(asset):
    if not isinstance(asset, Asset):
        raise ValueError('invalid asset')
    return PFX_ASSET + asset.get_digest(binary=True)



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
    :todo: optimize replacing asset stub with deserialized asset
    """
    def get_entry(self, entry, acl=None):
        k = pfx_entry(self.ledger, entry)
        v = self.__o.get(k)
        entry = Entry.unwrap(v)
        # TODO: hacky!
        i = 0
        for o in entry.attachment:
            asset = self.get_asset(o)
            #asset = Asset.deserialize(v, digest=o.get_digest(binary=True))
            entry.attachment[i] = asset
            i += 1
        #entry.verify(acl=acl)
        return entry


    """Add an entry attachment asset to the store.

    :param asset: Asset containing digest to restore.
    :type asset: usawa.Asset
    :raises: FileExistsError if entry is already in store.
    """
    def add_asset(self, asset):
        k = pfx_asset(asset)
        v = asset.serialize()
        self.__o.put(k, v)


    """Restore an entry attachment asset from the store.
    """
    def get_asset(self, asset):
        k = pfx_asset(asset)
        v = self.__o.get(k)
        digest = asset.get_digest(binary=True)
        return Asset.deserialize(v, digest)


    """Load all entries from store, oldest to newest.

    Must be called on an unused ledger instance. Using with a ledger that contains or has contains entries is undefined.

    :raises FileNotFoundError: If an entry cannot be found.
    """
    def load(self, acl=None):
        logg.debug('load ledger from store {}'.format(self.ledger))
        while True:
            o = None
            try:
                o = self.get_entry(self.ledger.next_serial(), acl=acl)
            except FileNotFoundError:
                break
            self.ledger.add_entry(o)


    """Load all entries from store, newest to oldest.

    Must be called on an unused ledger instance. Using with a ledger that contains or has contains entries is undefined.

    :raises FileNotFoundError: If an entry cannot be found.
    """
    def restore(self, until=0, acl=None):
        logg.debug('restore ledger from store {}'.format(self.ledger))
        i = self.ledger.current_serial()
        while i > until: 
            logg.debug('get entry serial {} ledger {}'.format(i, self.ledger))
            #try:
            o = self.get_entry(i, acl=acl)
            #except FileNotFoundError:
            #    break
            self.ledger.add_entry(o, check_parent=False)
            i -= 1


    """Add signing key to the store.

    If this is the first key in the store, it will be set as default.

    :param wallet: The wallet object to store keys for.
    :type wallet: usawa.Wallet implementation
    :param acl: Access control list data to retrieve the allowance and label for the key.
    :type acl: usawa.ACL
    :param default: If True, this key will be set as default key.
    :type default: bool
    :param passphrase: Passphrase to encrypt the key with.
    :type passphrase: bytes
    :todo: Implement the ACL lookup
    """
    def add_key(self, wallet, acl=None, default=False, passphrase=None):
        k = pfx_key()
        try:
            self.__o.get(k)
        except FileNotFoundError:
            default = True
        pubkey = wallet.pubkey()
        if default:
            self.__o.put(k, pubkey, exist_ok=True)
        k = pfx_key(pubkey=pubkey)
        v = wallet.export(passphrase=passphrase)
        self.__o.put(k, v)


    """Get a newly instantiated wallet object from a private key in the store.
    
    If public key is not supplied, will retrieve the default private key.

    :param wallet_class: Wallet class to use to instantiate a Wallet object from private key material.
    :type: usawa.crypto.Wallet
    :param pubkey: Public key to retrieve private key for.
    :type pubkey: bytes
    :param passphrase: Passphrase to decrypt the key with.
    :type passphrase: bytes
    :raises FileNotFoundError: No key exists.
    :raises usawa.error.VerifyError: Key decryption failed.
    :return: Resulting wallet
    :rtype: usawa.crypto.Wallet
    """
    def get_key(self, wallet_class, pubkey=None, passphrase=None):
        if pubkey == None:
            k = pfx_key()
            pubkey = self.__o.get(k)
        k = pfx_key(pubkey=pubkey)
        #return self.__o.get(k)
        r = self.__o.get(k)
        return wallet_class.from_export(r, passphrase=passphrase)


    """Implements whee.Interface.put
    """
    def put(self, k, v):
        return self.__o.put(k, v)


    """Implements whee.Interface.get
    """
    def get(self, k):
        return self.__o.get(k)


    """Store all entries in the ledger state.

    Errors due to duplicate entry and asset insert attempts will be ignored.

    :param store_assets: Add all attachment assets from each entry.
    :type store_assets: boolean
    :raises FileExistsError: If duplicate entry is found.
    """
    def put_all(self, store_assets=False):
        for k in self.ledger.entries.keys():
            entry = self.ledger.entries[k]
            try:
                self.add_entry(entry, update_ledger=False)
            except FileExistsError as e:
                logg.info('putall skip duplicate entry {}'.format(entry))
            for asset in entry.attachment:
                try:
                    self.add_asset(asset)
                except FileExistsError:
                    logg.info('putall skip duplicate asset {}'.format(asset))
