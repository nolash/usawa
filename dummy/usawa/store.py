import enum
import os

from whee import Interface

from .ledger import Ledger
from .entry import Entry


PFX_LEDGER = b'\x01'
PFX_LEDGER_LOCK = b'\x02'
PFX_ENTRY = b'\x04'


def pfx_ledger_topic(topic):
    r = PFX_LEDGER + topic
    return r

def pfx_ledger_lock(topic):
    r = PFX_LEDGER_LOCK + topic
    return r


def pfx_ledger(ledger):
    if not isinstance(ledger, Ledger):
        raise ValueError('invalid ledger')
    return pfx_ledger_topic(topic)


def pfx_entry(ledger, entry):
    if not isinstance(entry, Entry):
        raise ValueError('invalid entry')
    if not isinstance(ledger, Ledger):
        raise ValueError('invalid ledger')
    return PFX_LEDGER + ledger.topic + entry.serial.to_bytes(8, byteorder='big')


class LedgerStore(Interface):

    def __init__(self, implementation, ledger):
        if not isinstance(implementation, Interface):
            raise ValueError('store must be whee interface instance')
        if not isinstance(ledger, Ledger):
            raise ValueError('invalid ledger')
        self.ledger = ledger
        self.__o = implementation


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


    def unlock(self):
        k = pfx_ledger_lock(self.ledger.topic)
        v = self.__o.delete(k)


    def add_entry(self, entry):
        k = pfx_entry(self.ledger, entry)
        v = entry.wrap()
        self.__o.put(k, v)
