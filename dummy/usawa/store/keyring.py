import logging
import base64

import keyring
from whee import Interface

from .prefix import *

logg = logging.getLogger('usawa.store.keyring')


class KeyringBaseStore(Interface):

    def __init__(self, domain, implementation):
        if not isinstance(domain, str):
            raise ValueError('domain must be string')
        if len(domain) == 0:
            raise ValueError('domain cannot be empty string')
        logg.debug('initialied keyring base store domain {} with keyring {}'.format(domain, keyring.get_keyring()))
        self.domain = 'usawa.' + domain
        self.db = implementation


    def get(self, k):
        if not isinstance(k, str):
            k = k.hex()
        bytes.fromhex(k)
        v = keyring.get_password(self.domain, k)
        if v == None:
            return None
        return base64.b64decode(v)


    def put(self, k, v):
        if not isinstance(k, str):
            k = k.hex()
        bytes.fromhex(k)
        #k = self.domain + '.' + k
        v = base64.b64encode(v)
        return keyring.set_password(self.domain, k, v)


    def unlock(self):
        pass


    def lock(self):
        pass


class KeyringStore(KeyringBaseStore):

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
            self.get(k)
        except FileNotFoundError:
            default = True
        pubkey = wallet.pubkey()
        if default:
            self.put(k, pubkey, exist_ok=True)
        k = pfx_key(pubkey=pubkey)
        v = wallet.export(passphrase=passphrase, opslimit=opslimit, memlimit=memlimit)
        self.put(k, v)


    def reencrypt_key(self, wallet_class, pubkey, passphrase_new=None, passphrase_cur=None, opslimit=0, memlimit=0):
        wallet = self.get_key(wallet_class, pubkey, passphrase=passphrase_cur)
        k = pfx_key(pubkey=pubkey)
        v = wallet.export(passphrase=passphrase_new, opslimit=opslimit, memlimit=memlimit)
        self.put(k, v, exist_ok=True)
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
            pubkey = self.get(k)
        k = pfx_key(pubkey=pubkey)
        #return self.db.get(k)
        r = self.get(k)
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
