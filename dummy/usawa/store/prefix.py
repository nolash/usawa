import uuid

from usawa import Entry, Asset, Ledger

PFX_KEY = b'\x00'
PFX_LEDGER = b'\x01'
PFX_LEDGER_INDEX = b'\x02'
PFX_LEDGER_LOCK = b'\x03'
PFX_ENTRY = b'\x04'
PFX_ENTRY_LINK = b'\x05'
PFX_UNIT_INDEX = b'\x08'
PFX_ASSET = b'\x10'
PFX_ASSET_INDEX = b'\x11'


"""DB key prefix for a private key entry

If public key is not specified, the prefix will reference the DEFAULT key.

:param pubkey: Public key to get private key for.
:type pubkey: bytes
:return: DB prefix
:rtype: bytes
"""
def pfx_key(pubkey=None):
    v = PFX_KEY
    if pubkey == None:
        return v
    return v + pubkey


"""DB key prefix for the ledger state of a topic.

:param topic: Legder topic.
:type topic: bytes
:return: DB prefix
:rtype: bytes
"""
def pfx_ledger_topic(topic):
    r = PFX_LEDGER + topic
    return r


"""DB key prefix for locking the ledger state of a topic.

:param topic: Legder topic.
:type topic: bytes
:return: DB prefix
:rtype: bytes
"""
def pfx_ledger_lock(topic):
    r = PFX_LEDGER_LOCK + topic
    return r


"""DB key prefix for adding an entry to a ledger.

:param ledger: Ledger object.
:type ledger: usawa.Ledger
:param entry: Entry object to add to ledger.
:type entry: usawa.Entry
:raises ValueError: Invalid ledger or entry
:return: DB prefix
:rtype: bytes
"""
def pfx_entry(ledger, entry):
    serial = 0
    if isinstance(entry, Entry):
        serial = entry.serial
    elif isinstance(entry, int):
        serial = entry
    else:
        raise ValueError('invalid entry')
    if not isinstance(ledger, Ledger):
        raise ValueError('invalid ledger')
    return PFX_LEDGER + ledger.topic + serial.to_bytes(8, byteorder='big')


"""DB key prefix for adding a WIP entry object.

:param entry: Entry draft object to add to store.
:type entry: usawa.Entry
:raises ValueError: Invalid ledger or entry
:return: DB prefix
:rtype: bytes
"""
def pfx_entry_draft(entry):
    if not isinstance(entry, Entry):
        raise ValueError('invalid entry')
    ref = entry.get_ref(binary=True)
    return PFX_ENTRY + ref

"""DB key prefix for adding entry attachment asset to a ledger.

"""
def pfx_asset(asset):
    if not isinstance(asset, Asset):
        raise ValueError('invalid asset')
    digest = asset.get_digest(binary=True)
    return PFX_ASSET + digest


def pfx_asset_index(asset):
    if not isinstance(asset, Asset):
        raise ValueError('invalid asset')
    return PFX_ASSET_INDEX + asset.get_ref(binary=True)


def pfx_entry_link(ref):
    if isinstance(ref, str):
        ref = uuid.UUID(ref)
    if isinstance(ref, uuid.UUID):
        ref = ref.bytes
    else:
        uu = uuid.UUID(bytes=ref)
        ref = uu.bytes
    return PFX_ENTRY_LINK + ref



