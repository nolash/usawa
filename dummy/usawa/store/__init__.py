import enum
import os
import logging

from whee import Interface

from usawa.ledger import Ledger
from usawa.entry import Entry
from usawa.asset import Asset
from usawa.link import EntryLink
from .prefix import *


logg = logging.getLogger('usawa.store')


class BaseStore(Interface):

    def __init__(self, implementation):
        if not isinstance(implementation, Interface):
            raise ValueError('store must be whee interface instance')
        self.db = implementation


    """Implements whee.Interface.put
    """
    def put(self, k, v):
        return self.db.put(k, v)


    """Implements whee.Interface.get
    """
    def get(self, k):
        return self.db.get(k)


    """Implements whee.Interface.lock
    """
    def lock(self):
        k = pfx_ledger_lock(self.ledger.topic)
        v = None
        # TODO: needs to be an atomic routine
        try:
            v = self.db.get(k)
        except KeyError:
            raise PermissionError()
        self.db.put(k, 0x01, exist_ok)
        # atomic until here


    """Implements whee.Interface.unlock
    """
    def unlock(self):
        k = pfx_ledger_lock(self.ledger.topic)
        v = self.db.delete(k)


class KeyStore(BaseStore):

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
    def add_key(self, wallet, acl=None, default=False, passphrase=None, opslimit=0, memlimit=0):
        k = pfx_key()
        try:
            self.db.get(k)
        except FileNotFoundError:
            default = True
        pubkey = wallet.pubkey()
        if default:
            self.db.put(k, pubkey, exist_ok=True)
        k = pfx_key(pubkey=pubkey)
        v = wallet.export(passphrase=passphrase, opslimit=opslimit, memlimit=memlimit)
        self.db.put(k, v)


    def reencrypt_key(self, wallet_class, pubkey, passphrase_new=None, passphrase_cur=None, opslimit=0, memlimit=0):
        wallet = self.get_key(wallet_class, pubkey, passphrase=passphrase_cur)
        k = pfx_key(pubkey=pubkey)
        v = wallet.export(passphrase=passphrase_new, opslimit=opslimit, memlimit=memlimit)
        self.db.put(k, v, exist_ok=True)
        return wallet


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
    def get_key(self, wallet_class, pubkey=None, passphrase=None, opslimit=0, memlimit=0):
        if pubkey == None:
            k = pfx_key()
            pubkey = self.db.get(k)
        k = pfx_key(pubkey=pubkey)
        #return self.db.get(k)
        r = self.db.get(k)
        return wallet_class.from_export(r, passphrase=passphrase, opslimit=opslimit, memlimit=memlimit)


    """Get the public key of the default key in the store.

    :param wallet_class: Wallet class to use to instantiate a Wallet object from private key material.
    :type: usawa.crypto.Wallet
    :raises FileNotFoundError: No key exists.
    :return: Resulting wallet
    :rtype: usawa.crypto.Wallet
    """
    def get_default_key(self, wallet_class):
        k = pfx_key()
        pubkey = self.db.get(k)
        return wallet_class(publickey=pubkey)


class AssetStore(BaseStore):

    """Add an entry attachment asset to the store.

    :param asset: Asset containing digest to restore.
    :type asset: usawa.Asset
    :raises: FileExistsError if entry is already in store.
    """
    def add_asset(self, asset, overwrite=False):
        k = pfx_asset(asset)
        v = asset.serialize()
        self.db.put(k, v, exist_ok=overwrite)
        v = k
        k = pfx_asset_index(asset)
        self.db.put(k, v, exist_ok=True)


    """Restore an entry attachment asset from the store.
    """
    def get_asset(self, asset):
        k = pfx_asset(asset)
        v = self.db.get(k)
        digest = asset.get_digest(binary=True)
        return Asset.deserialize(v, digest)


    """Restore an entry attachment asset from the store using the reference index.
    """
    def get_asset_indexed(self, asset):
        k = pfx_asset_index(asset)
        k = self.db.get(k)
        v = self.db.get(k)
        return Asset.deserialize(v, k[1:])



class LinkStore(BaseStore):

    def put_link(self, link, refs=None):
        if refs == None:
            refs = link.refs()
        elif isinstance(refs, str):
            refs = [refs]
        for ref in refs:
            v = link.serialize_for(ref)
            k = pfx_entry_link(ref)
            self.db.put(k, v, exist_ok=True)


    def get_link(self, link, refs=None):
        if isinstance(refs, str):
            refs = [refs]
        elif refs == None:
            raise NotImplementedError('load all links not implemented yet')
        for ref in refs:
            k = pfx_entry_link(ref)
            v = self.db.get(k)
            link.deserialize_for(ref, v)


class EntryStore(KeyStore, LinkStore):

    # TODO: this will overwrite the draft when the entry has a serial, but on check is being performed that the ledger entry was actually added.
    def put_draft(self, entry):
        k = pfx_entry_draft(entry)
        if entry.serial > -1:
            return self.db.put(k, b'\x00', exist_ok=True)
        v = entry.serialize()
        self.db.put(k, v, exist_ok=True)


    def get_draft(self, entry, unitindex=None):
        k = pfx_entry_draft(entry)
        v = self.db.get(k)
        if len(v) == 1:
            return None
        entry = Entry.deserialize(v, unitindex=unitindex)
        # TODO: hacky!
        i = 0
        for o in entry.attachment:
            asset = self.get_asset(o)
            entry.attachment[i] = asset
            i += 1
        return entry


    """Add an entry to the store.

    :param entry: Entry to add.
    :type entry: usawa.Entry or int
    :param update_ledger: Add the underlying ledger object with the entry.
    :type update_ledger: boolean
    :raises: ValueError if the entry is not the right object type.
    :raises: FileExistsError if entry is already in store.
    """
    def add_entry(self, entry, update_ledger=False, overwrite=False, linker=None, update_link=False):
        k = pfx_entry(self.ledger, entry)
        v = entry.wrap(linker=linker)
        self.db.put(k, v, exist_ok=overwrite)
        if update_ledger:
            self.ledger.add_entry(entry)
        if update_link:
            self.put_link(linker, refs=linker.get(entry))


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
    def get_entry(self, entry, acl=None, unitindex=None, linker=None):
        k = pfx_entry(self.ledger, entry)
        v = self.db.get(k)
        entry = Entry.unwrap(v, unitindex=unitindex, linker=linker)
        # TODO: hacky!
        i = 0
        for o in entry.attachment:
            asset = self.get_asset(o)
            #asset = Asset.deserialize(v, digest=o.get_digest(binary=True))
            entry.attachment[i] = asset
            i += 1
        return entry


class LedgerStore(EntryStore, AssetStore):
    """Wrapper for an implementation of the whee store that handles encoding of ledgers and entries.

    :param implementation: Store implementation.
    :type implementation: whee.Interface (implementation)
    :param ledger: The ledger for which to execute store operations.
    :type ledger: usawa.Ledger
    """
    def __init__(self, implementation, ledger):
        super(LedgerStore, self).__init__(implementation)
        if not isinstance(ledger, Ledger):
            raise ValueError('invalid ledger')
        self.ledger = ledger


    """Implements whee.Interface.start
    """
    def start(self):
        serial = 0
        k = pfx_ledger_topic(self.ledger.topic)
        try:
            b = self.db.get(k)
            serial = int.from_bytes(8, byteorder='big')
        except FileNotFoundError:
            v = serial.to_bytes(8, byteorder='big')
            self.db.put(k, v)
        self.ledger.serial = serial


    """Commits the ledger state to store as an XML snapshot.

    """
    def save_state(self):
        r = self.ledger.sign()
        v = self.ledger.to_string(as_bytes=True)
        k = pfx_ledger_topic(self.ledger.topic)
        self.db.put(k, v, exist_ok=True)


    """Create a new ledger store from topic.

    Loads the last state of the ledger saved with save_state.

    :param db: Database implementation
    :type db: whee.Interface (implementation)
    :param topic: The ledger topic to restore state for.
    :type topic: 32 byte string.
    :raises FileNotFoundError: 
    """
    @staticmethod
    def from_state(db, topic, reset=False):
        k = pfx_ledger_topic(topic)
        v = db.get(k)
        o = Ledger.from_string(v.decode('utf-8'))
        if reset:
            logg.debug('reset ledger state from store topic {}'.format(o.topic))
            o = Ledger(o.uidx, topic=o.topic)
        return LedgerStore(db, o)


    """Load all entries from store, oldest to newest.

    Must be called on an unused ledger instance. Using with a ledger that contains or has contains entries is undefined.

    :raises FileNotFoundError: If an entry cannot be found.
    """
    def load(self, acl=None, until=0, unitindex=None, entry_callback_pre=None, entry_callback_post=None, linker=None):
        logg.debug('load ledger from store {} until {}'.format(self.ledger, until))
        v = 0
        while True:
            o = None
            try:
                if until != 0:
                    if until == v:
                        break
                v = self.ledger.peek()
                o = self.get_entry(v, acl=acl, unitindex=unitindex, linker=linker)
                self.ledger.next_serial()
            except FileNotFoundError as e:
                logg.debug('entry serial {} not found, terminating ({})'.format(v, e))
                break
            if entry_callback_pre != None:
                entry_callback_pre(o)
            logg.debug("load entry {}".format(o.to_string(canon=True)))
            self.ledger.add_entry(o)
            if entry_callback_post != None:
                entry_callback_post(o)
        logg.info('loaded ledger {}'.format(self.ledger))


    """Load all entries from store, newest to oldest.

    Must be called on an unused ledger instance. Using with a ledger that contains or has contains entries is undefined.

    :raises FileNotFoundError: If an entry cannot be found.
    """
    def restore(self, until=0, acl=None, linker=None):
        logg.debug('restore ledger from store {}'.format(self.ledger))
        i = self.ledger.current_serial()
        while i > until: 
            logg.debug('get entry serial {} ledger {}'.format(i, self.ledger))
            #try:
            o = self.get_entry(i, acl=acl, linker=linker)
            #except FileNotFoundError:
            #    break
            self.ledger.add_entry(o, check_parent=False)
            i -= 1


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
