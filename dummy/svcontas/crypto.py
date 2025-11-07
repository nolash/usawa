import nacl.signing

AXX_ALL = 0xffffffff


class DemoWallet:

    def __init__(self, privatekey=None, publickey=None):
        publickey_chk = None
        if privatekey == None:
            if publickey == None:
                privatekey = nacl.signing.SigningKey.generate()
        if privatekey != None:
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
        r = self.pk.sign(v)
        return r.signature


    def pubkey(self):
        return self.pubk.encode()


    def verify(self, v, sig):
        return self.pubk.verify(v, sig)


class ACL:

    def __init__(self):
        self.axx = {}


    def add(self, who, what=None, label=None):
        if label == None:
            label = who
        if what == None:
            what = AXX_ALL
        self.axx[label] = (who, what,)


    def may(self, who, what):
        label = who
        if isinstance(label, bytes):
            label = who.hex()
        return (self.axx[label][1] & what) == what


    def pubkeys(self, binary=True):
        r = []
        for k in self.axx.values():
            v = k[0]
            if not binary:
                v = v.hex()
            r.append(v)
        return r
