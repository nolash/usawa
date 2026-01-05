import logging

import nacl.signing

AXX_ALL = 0xffffffff
AXX_ANY = 0x01

logg = logging.getLogger('crypto')


class Wallet:
    """Wallet is an unimplemented class defining the interface for wallet operations.
    """

    def sign(self, v):
        """Sign data with the wallet's private key.

        :returns: Signature data.
        :rtype: bytes
        :todo: Raise local error if sign fail
        """
        raise NotImplementedError


    def pubkey(self):
        """Return the public key data in the wallet.

        :returns: Public key data.
        :rtype: bytes
        :todo: Raise local error if sign fail
        """
        raise NotImplementedError


    def privkey(self):
        """Return the private key data in the wallet.
        
        :returns: Private key data.
        :rtype: bytes
        :todo: Raise local error if sign fail
        """
        raise NotImplementedError


    def verify(self, v, sig):
        """Verify signature data against the given message.

        :returns: True if signature is valid.
        :rtype: boolean
        """
        raise NotImplementedError


class DemoWallet(Wallet):
    """DemoWallet is an unsafe wallet implementation used during development. It implements the Wallet interface class.
    """

    def __init__(self, privatekey=None, publickey=None):
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
                raise AttributeError('wallet must be created with either public or private key')
            publickey = publickey_chk    
        elif publickey_chk != None and publickey != publickey_chk.encode():
            raise ValueError('publickey supplied does not match privatekey')
        else:
            publickey = nacl.signing.VerifyKey(publickey)
        self.pubk = publickey
  

    def sign(self, v):
        """Implements usawa.Wallet.sign
        """
        r = self.pk.sign(v)
        return r.signature


    def pubkey(self):
        """Implements usawa.Wallet.pubkey
        """
        return self.pubk.encode()


    def privkey(self, passphrase=None):
        """Implements usawa.Wallet.privkey
        """
        return self.pk.encode()

    def verify(self, v, sig):
        """Implements usawa.Wallet.verify
        """
        #return self.pubk.verify(v, sig)
        self.pubk.verify(v, sig)
        return True


class ACL:
    """ACL defines public keys to accept signatures from, and for which purpose.

    :todo: Implement signing purpose distinction.
    """

    def __init__(self):
        self.axx = {}
        self.rev = {}


    def add(self, who, what=None, label=None):
        """Add a public key to the trusted list of keys.

        :param who: Binary or hexadecimal public key data.
        :type who: str or bytes
        :param what: A bit-field representing what purpose key may be used.
        :type what: bytes
        :param label: A human-readable string describing the public key identity.
        :type label: str
        """
        if isinstance(who, bytes):
            who = who.hex()
        if label == None:
            label = who
        if what == None:
            what = AXX_ALL
        logg.info('add acl line "{}" ({}): {}'.format(label, who, what))
        self.axx[label] = (who, what,)
        self.rev[who] = label


    def have(self, who):
        """Check whether the given public key identity is in the trusted key list.

        :param who: Binary or hexadecimal public key data.
        :type who: str or bytes
        :returns: True if found.
        :rtype: boolean
        """
        if isinstance(who, bytes):
            who = who.hex()
        return self.rev[who]


    def may(self, who, what):
        """Check if key is valid for the given purpose.

        :param who: Binary or hexadecimal public key data.
        :type who: str or bytes
        :returns: 0 if key not found. Otherwise True key is valid for purpose.
        :rtype: bool or int
        """
        label = who
        if isinstance(label, bytes):
            label = who.hex()
        try:
            return (self.axx[label][1] & what) == what
        except KeyError:
            return 0


    def pubkeys(self, binary=True):
        """Return all public keys currently in list.

        :param binary: If True, return in binary format. Return in hex otherwise.
        :type binary: boolean
        :returns: A list of public keys.
        :rtype: list of str or bytes
        :todo: Filter by purpose.
        """
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
