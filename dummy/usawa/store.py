import enum
import os

from whee import Interface

from .ledger import Ledger
from .entry import Entry


PFX_LEDGER = b'\x01'
PFX_LEDGER_LOCK = b'\x02'
PFX_ENTRY = b'\x04'


def pfx_ledger_topic(topic):
    """Return ledger store prefix for topic.

    :params topic: Topic to generate prefix for.
    :type topic: bytes
    :returns: Prefix.
    :rtype: bytes
    """
    r = PFX_LEDGER + topic
    return r

def pfx_ledger_lock(topic):
    """Return ledger store locking prefix for topic.

    :params topic: Topic to generate prefix for.
    :type topic: bytes
    :returns: Prefix.
    :rtype: bytes
    """
    r = PFX_LEDGER_LOCK + topic
    return r


#def pfx_ledger(ledger):
#    if not isinstance(ledger, Ledger):
#        raise ValueError('invalid ledger')
#    return pfx_ledger_topic(topic)


def pfx_entry(ledger, entry):
    """Return ledger store prefix for an entry.

    :param ledger: Ledger context for the entry.
    :type ledger: usawa.Ledger
    :param entry: Entry to create prefix for.
    :type entry: usawa.Entry
    :returns: Prefix.
    :rtype: bytes
    """
    if not isinstance(entry, Entry):
        raise ValueError('invalid entry')
    if not isinstance(ledger, Ledger):
        raise ValueError('invalid ledger')
    return PFX_LEDGER + ledger.topic + entry.serial.to_bytes(8, byteorder='big')


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


    # WIP implementation of couchdb?
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


    # WIP implementation of couchdb?
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


    # WIP implementation of couchdb?
    def unlock(self):
        k = pfx_ledger_lock(self.ledger.topic)
        v = self.__o.delete(k)


    """Add an entry to the store.

    :param entry: Entry to add.
    :type entry: usawa.Entry
    :raises: FileExistsError if entry is already in store.
    """
    def add_entry(self, entry):
        k = pfx_entry(self.ledger, entry)
        v = entry.wrap()
        self.__o.put(k, v)
