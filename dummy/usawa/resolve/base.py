import hashlib

import hexathon

from usawa.error import VerifyError


def sha512_verify(k, v=None):
    if isinstance(k, str):
        k = bytes.fromhex(k)
    if len(k) != 64:
            raise ValueError('expect 512 bit key')
    khx = hexathon.uniform(k.hex())
    if v != None:
        h = hashlib.sha512()
        h.update(v)
        if k != h.digest():
            raise VerifyError(khx)
    return khx


class BaseResolver:

    def get(self, k, v, verifier=None):
        raise NotImplementedError()


    def put(self, k):
        raise NotImplementedError()


    def delete(self, k):
        raise NotImplementedError()
