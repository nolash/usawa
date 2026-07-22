import logging
import hashlib
import os

import rencode
import lxml.etree

import nacl.signing
import nacl.secret
import nacl.exceptions
from nacl.pwhash import argon2i

from usawa.error import VerifyError

AXX_ALL = 0xFFFFFFFF
AXX_ANY = 0x01

DEFAULT_DID = "usawa"

logg = logging.getLogger("crypto")


class DID:
    """Represents a method and endpoint pair for a Decentralized IDentifier resource.

    Using default values implies that integrated tools for usawa library and executable will be used.

    DID v1.0 is specified in https://www.w3.org/TR/did-1.0/

    :param v: The endpoint value of the method.
    :type v: str
    :param method: DID method
    :type method: str
    """

    def __init__(self, v="_", method=DEFAULT_DID):
        self.v = v
        self.m = method

    """Return DID method

    :returns: Method
    :rtype :str
    """

    def method(self):
        return self.m

    def __str__(self):
        return "did:" + self.m + ":" + self.v


def key_from_export(v, passphrase="", did=None, opslimit=0, memlimit=0):
    if passphrase is None:
        passphrase = b""
    if isinstance(passphrase, str):
        passphrase = passphrase.encode("utf-8")

    salt = v[: argon2i.SALTBYTES]
    ciphertext = v[argon2i.SALTBYTES:]
    if not opslimit:
        opslimit = nacl.pwhash.OPSLIMIT_MODERATE
    if not memlimit:
        memlimit = nacl.pwhash.MEMLIMIT_MODERATE
    
    #logg.debug('pwhash ops {} mem {} salt {} pp {}'.format(opslimit, memlimit, salt, passphrase))
    logg.debug('pwhash ops {} mem {} salt {}'.format(opslimit, memlimit, salt))

    key = argon2i.kdf(nacl.secret.SecretBox.KEY_SIZE, passphrase, salt, opslimit=opslimit, memlimit=memlimit)

    box = nacl.secret.SecretBox(key)
    try:
        r = box.decrypt(ciphertext)
    except nacl.exceptions.CryptoError:
        raise VerifyError("decrypt fail")
    return r


class Wallet:
    """Wallet is an unimplemented class defining the interface for wallet operations."""

    """Get the did URI for the wallet identity.

    :param did: An optional DID object to apply. Default is a DID object with default values.
    :type did: usawa.DID
    :return: DID URI
    :rtype: str
    """

    def __init__(self, did=None):
        if did == None:
            did = DID()
        self.didval = did

    """Return the DID object for the wallet.

    :return: DID
    :rtype: usawa.DID
    """

    def did(self):
        return self.didval

    """Return the method part of the DID wallet.

    :return: DID method
    :rtype: str
    """

    def did_method(self):
        return self.didval.method()

    """Return the endpoint part of the DID wallet.

    :return: DID method
    :rtype: str
    """

    def did_uri(self):
        return str(self.didval)

    """Return the well-known identifier for a signature produced by the wallet.

    By default this is the same as the public key of the wallet.

    :return: Wallet identifier
    :rtype: bytes
    """

    def address(self):
        return self.pubkey()

    """Sign data with the wallet's private key.

    Depending on the signature algorithm, the data provided may or may not be hashed.

    :param v: Data to sign.
    :type v: bytes
    :returns: Signature data.
    :rtype: bytes
    :todo: Raise local error if sign fail
    """
    def sign(self, v):
        raise NotImplementedError


    """Return the public key data in the wallet.

    :returns: Public key data.
    :rtype: bytes
    :todo: Raise local error if sign fail
    """
    def pubkey(self):
        raise NotImplementedError

    """Return the private key data in the wallet.
        
    :returns: Private key data.
    :rtype: bytes
    :todo: Raise local error if sign fail
    """
    def privkey(self):
        raise NotImplementedError


    """Verify signature data against the given message.

    :param v: Data to verify
    :type v: bytes
    :param sig: Signature data
    :type sig: bytes
    :returns: True if signature is valid.
    :rtype: boolean
    """

    def verify(self, v, sig):
        raise NotImplementedError


    def export(self, passphrase=None, opslimit=0, memlimit=0):
        if passphrase is None:
            passphrase = b""
        if isinstance(passphrase, str):
            passphrase = passphrase.encode("utf-8")
        if len(passphrase) == 0:
            logg.warning("exporting key with no passphrase")

        salt = os.urandom(argon2i.SALTBYTES)
        if opslimit == 0:
            opslimit = nacl.pwhash.OPSLIMIT_MODERATE
        if memlimit == 0:
            memlimit = nacl.pwhash.MEMLIMIT_MODERATE
        #logg.debug('pwhash ops {} mem {} salt {} pw {}'.format(opslimit, memlimit, salt, passphrase.hex()))
        logg.debug('pwhash ops {} mem {} salt {}'.format(opslimit, memlimit, salt))
        key = argon2i.kdf(nacl.secret.SecretBox.KEY_SIZE, passphrase, salt, opslimit=opslimit, memlimit=memlimit)
        box = nacl.secret.SecretBox(key)
        k = self.privkey()
        r = box.encrypt(k)
        return salt + r  # prepend salt


    @staticmethod
    def from_export(v, passphrase=None, **kwargs):
        raise NotImplementedError()


    """Generate an identity XML tree entry from the wallet.

    The element generated is valid to be inserted as an identity sub-element in the ledger element.

    :returns: XML tree.
    :rtype: lxml.etree.Element
    """

    def to_tree(self):
        pubkey = self.pubkey()
        o = lxml.etree.Element("identity")
        o.set("keyid", pubkey.hex())
        did = self.did()
        o.set("didtype", did.method())
        return o

    def __str__(self):
        return self.did_uri()


class DemoWallet(Wallet):
    """DemoWallet is an unsafe wallet implementation used during development. It implements the Wallet interface class.

    If private key is passed, the public key of the private key will be used (and the publickey parameter will be ignored).

    If only public key is passed, wallet will not be able to sign.

    :param privatekey: Private key data to use for wallet operations.
    :type privatekey: bytes
    :param publickey: Private key data to use for wallet operations.
    :type publickey: bytes
    :param did: DID object (see usawa.Wallet for details).
    :type did: usawa.DID
    """

    def __init__(self, privatekey=None, publickey=None, did=None):
        super(DemoWallet, self).__init__(did=did)
        self.pk = None
        publickey_chk = None
        if privatekey == None:
            if publickey == None:
                self.pk = nacl.signing.SigningKey.generate()
                publickey_chk = self.pk.verify_key
        else:
            self.pk = nacl.signing.SigningKey(privatekey)
            publickey_chk = self.pk.verify_key

        if publickey == None:
            if publickey_chk == None:
                raise AttributeError(
                    "wallet must be created with either public or private key"
                )
            publickey = publickey_chk
        elif publickey_chk != None and publickey != publickey_chk.encode():
            raise ValueError("publickey supplied does not match privatekey")
        else:
            publickey = nacl.signing.VerifyKey(publickey)
        self.pubk = publickey
        self.didval = DID(v=self.pubkey().hex())
        logg.debug("wallet created {}".format(self.pubkey().hex()))

    """Implements usawa.Wallet.sign
    """

    def sign(self, v):
        r = self.pk.sign(v)
        return r.signature

    """Implements usawa.Wallet.sign
    """

    def pubkey(self):
        """Implements usawa.Wallet.pubkey"""
        return self.pubk.encode()

    """Implements usawa.Wallet.privkey
    """

    def privkey(self, passphrase=None):
        return self.pk.encode()

    """Implements usawa.Wallet.verify
    """

    def verify(self, v, sig):
        r = False
        try:
            self.pubk.verify(v, sig)
            r = True
        except nacl.exceptions.BadSignatureError:
            pass
        return r

    @staticmethod
    def from_export(v, passphrase=None, opslimit=0, memlimit=0):
        k = key_from_export(v, passphrase=passphrase, opslimit=opslimit, memlimit=memlimit)
        return DemoWallet(privatekey=k)


class ACL:
    """ACL defines public keys to accept signatures from, and for which purpose.

    :todo: Implement signing purpose distinction.
    """

    def __init__(self):
        self.axx = {}
        self.rev = {}
        self.dids = {}

    """Create an ACL object from a wallet.

    The what parameter specified which actions the wallet identifier can sign off on in the given context.

    :param wallet: Wallet to read verifying key from
    :type wallet: usawa.Wallet
    :param what: Bitfield defining credentials for the signing key.
    :type what: bytes
    :param label: Human-friendly name of the wallet identifier.
    :type label: str
    :todo: what should be an object
    """

    @staticmethod
    def from_wallet(wallet, what=None, label=None):
        o = ACL()
        o.add(wallet.pubkey(), what=what, label=label, did=wallet.did())
        return o

    """Retrieve DID for a wallet identifier.

    :param v: ID of the wallet.
    :type v: bytes
    :return: DID object
    :rtype: usawa.DID
    """

    def did(self, v):
        return self.dids[v]

    """Add a public key to the trusted list of keys.

    :param who: Binary or hexadecimal public key data.
    :type who: str or bytes
    :param what: A bit-field representing what purpose key may be used.
    :type what: bytes
    :param label: A human-readable string describing the public key identity.
    :type label: str
    :param did: DID to associate to ACL. See usawa.DID for more details on default values.
    :type did: usawa.DID
    """

    def add(self, who, what=None, label=None, did=DEFAULT_DID):
        if isinstance(who, str):
            who = bytes.fromhex(who)
        if label == None:
            label = who
        if what == None:
            what = AXX_ALL
        logg.info('add acl line "{}" ({}): {} did {}'.format(label, who, what, did))
        self.axx[label] = (
            who,
            what,
        )
        self.rev[who] = label
        self.dids[label] = did

    """Check whether the given public key identity is in the trusted key list.

    :param who: Binary or hexadecimal public key data.
    :type who: str or bytes
    :returns: True if found.
    :rtype: boolean
    """

    def have(self, who):
        if isinstance(who, str):
            who = bytes.fromhex(who)
        return self.rev[who]

    """Check if key is valid for the given purpose.

    :param who: Binary or hexadecimal public key data.
    :type who: str or bytes
    :param what: Specifier for credentials to test against.
    :type what: bytes
    :returns: 0 if key not found. Otherwise True key is valid for purpose.
    :rtype: bool or int
    """

    def may(self, who, what):
        label = who
        if isinstance(label, bytes):
            label = who.hex()
        try:
            return (self.axx[label][1] & what) == what
        except KeyError:
            return 0

    """Return all public keys currently in list.

    :param binary: If True, return in binary format. Return in hex otherwise.
    :type binary: boolean
    :returns: A list of public keys.
    :rtype: list of str or bytes
    :todo: Filter by purpose.
    """

    def pubkeys(self, binary=True):
        r = []
        for k in self.axx.values():
            v = k[0]
            if not binary:
                try:
                    v = v.hex()
                except AttributeError:
                    v = self.axx[self.rev[v]][0]
            r.append(v)
        return r

    """Generate the simple data structure used for rencode serialization.

    :returns: data structure
    :rtype: list
    """

    def to_list(self):
        keys = list(self.rev.keys())
        keys.sort()
        r = []
        for k in keys:
            v = self.axx[self.rev[k]][1]
            r.append(
                (
                    k,
                    v,
                )
            )
        return r

    """Generate the wire format for the ACL.

    :return: rencoded object
    :rtype: bytes
    """

    def serialize(self):
        r = self.to_list()
        return rencode.dumps(r)
