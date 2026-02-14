import os
import logging

from .base import BaseResolver, sha512_verify
from usawa.error import VerifyError

logg = logging.getLogger('usawa.fsresolver')


def normalize_keyname(k):
    if isinstance(k, bytes):
        k = k.hex()
    else:
        bytes.fromhex(k)
    return hexathon.uniform(k)


class FSResolver(BaseResolver):

    def __init__(self, path, verifier=sha512_verify):
        self.path = os.path.realpath(path)
        self.verifier = verifier
        os.makedirs(self.path, exist_ok=True)

    
    def get(self, k):
        khx = self.verifier(k)
        fp = os.path.join(self.path, khx)
        f = open(fp, 'rb')
        v = f.read()
        f.close()
        if not self.verifier(k, v):
            raise VerifyError(khx)
        return v


    def put(self, k, v):
        khx = self.verifier(k, v=v)
        fp = os.path.join(self.path, khx)
        f = open(fp, 'wb')
        c = f.write(v)
        logg.debug('{} bytes written for key {}'.format(c, k))
        f.close()
        return v
