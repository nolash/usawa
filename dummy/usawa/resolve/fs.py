import os
import logging

from .base import BaseResolver, sha512_verify
from usawa.error import VerifyError

logg = logging.getLogger('usawa.resolve.fs')


def normalize_keyname(k):
    if isinstance(k, bytes):
        k = k.hex()
    else:
        bytes.fromhex(k)
    return hexathon.uniform(k)


class FSResolver(BaseResolver):

    """Resolver implementation for a filesystem directory.

    If directory does not exist it will be created, along with any necessary ascendants.

    :param path: Path to directory to store under.
    :type path: str
    :raises PermissionError: Insufficient access to create directory.
    :seealso: usawa.resolve.BaseResolver
    """
    def __init__(self, path, verifier=sha512_verify):
        super(FSResolver, self).__init__(verifier=verifier)
        self.path = os.path.realpath(path)
        os.makedirs(self.path, exist_ok=True)

    
    """Implements usawa.resolve.BaseResolver
    """
    def get(self, k):
        khx = self.verifier(k)
        fp = os.path.join(self.path, khx)
        f = open(fp, 'rb')
        v = f.read()
        f.close()
        if not self.verifier(k, v):
            raise VerifyError(khx)
        return v


    """Implements usawa.resolve.BaseResolver
    """
    def put(self, k, v):
        khx = self.verifier(k, v=v)
        fp = os.path.join(self.path, khx)
        f = open(fp, 'wb')
        c = f.write(v)
        logg.debug('{} bytes written for key {}'.format(c, khx))
        f.close()
        return k


    """Implements usawa.resolve.BaseResolver
    """
    def have(self, k):
        r = -1
        if os.path.is_file():
            r = 1
        return r
