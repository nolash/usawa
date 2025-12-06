import enum
import os

from whee import Interface

from .ledger import Ledger
from .entry import Entry


PFX_LEDGER = b'\x01'
PFX_ENTRY = b'\x02'


def pfx_ledger_topic(topic):
    r = PFX_LEDGER + topic
    return r


def pfx_ledger(ledger):
    if not isintance(ledger, Ledger):
        raise ValueError('invalid ledger')
    return pfx_ledger_topic(topic)


def pfx_entry(ledger, entry):
    if not isintance(entry, Entry):
        raise ValueError('invalid entry')
    if not isintance(ledger, Ledger):
        raise ValueError('invalid ledger')


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


    def put(self):
        pass 
