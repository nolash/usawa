import hashlib
import logging

import hexathon

from usawa import Entry
from usawa.error import VerifyError
from usawa.constant import DEFAULTPARENT

logg = logging.getLogger('usawa.resolve')


"""Verifies a key as a sha512 digest, optionally against the given value.

:param k: Key to check.
:type k: bytes or hex string
:param v: Value to check against key.
:type v: bytes
:raises ValueError: Invalid key (not 512 bits)
:raises VerifyError: Value digest does not match key.
:return: Key as hex string
:rtype: str
"""
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

    """A resolver abstracts an immutable store used for storing asset data.

    Key/value pairs put to the store are checked by the verifier function before submission. Similarly, the value retrieved is checked by the verifier against the key used to get it.

    :raises IOError: Resolver backend unavailable, temporarily or permanently.
    :param verifier: Verifier function for checking keys and key/value relation.
    :type verifier: function, by default usawa.resolve.sha512_verify
    """
    def __init__(self, verifier=sha512_verify):
        self.verifier = verifier


    """Get value for key.

    :param k: Key
    :type k: bytes or hex string
    :raises FileNotFoundError: Key does not exist.
    :raises PermissionError: No access to data.
    :raises IOError: Any other read problem.
    :return: Value
    :rtype: bytes
    """
    def get(self, k):
        raise NotImplementedError()

    """Put value under key.

    Value may not be available immediately after method returns, since the implementation may store asynchronously.

    :param k: Key
    :type k: bytes or hex string
    :param v: Value
    :type v: bytes
    :raises FileExistsError: Key exists.
    :raises PermissionError: No access to data.
    :raises IOError: Any other read problem.
    :return: A textual representation of the key
    :rtype: str
    """
    def put(self, k, v):
        raise NotImplementedError()


    """Check availability of data without invoking a full get call.

    If -1 is returned, the key does not exist.

    If 0 is returned, the key has been added but may not yet be available for a get() call.

    If a value greater than 0 is returned, get() can safely be called.

    :param k: Key to check state for
    :type k: bytes or hex string
    :return: storage state
    :rtype: int
    """
    def state(self, k):
        raise NotImplementedError()


    def put_entry(self, entry, lookup=None):
        k = None
        (k, v) = entry.sum()
        self.put(k, v)
        if lookup != None:
            (k, v) = entry.get_lookup(lookup)
            self.put(k, v.encode('utf-8'))
            logg.debug('putentr entry {} {}'.format(k, v))
        return k


    def restore_ledger(self, ledger, min=0):
        lookup = self.get(ledger.lookup)
        while True:
            entry = Entry.from_string(lookup, ledger.uidx)
            if entry.serial == 0 or entry.serial < min:
                break
            k = entry.parent
            if k == DEFAULTPARENT:
                break
            logg.debug('getting parent {}'.format(k.hex()))
            v = self.get(k)
            entry_nolookup = Entry.from_string(v, ledger.uidx)
            lookup = self.get(entry_nolookup.lookup)

