import logging
from typing import List
from usawa.crypto import ACL, DemoWallet
from usawa.ledger import Ledger
from usawa.service import UnixClient
from usawa.store import LedgerStore
from ..core.models import LedgerEntry
from .entry_mapper import EntryMapper
from whee.valkey import ValkeyStore
from usawa import Ledger, DemoWallet, load

logg = logging.getLogger("storage.ledger_repository")


class LedgerRepository:
    """Repository that wraps LedgerStore and handles mapping"""
    
    def __init__(self,ledger_path = None, unix_client: UnixClient = None):
        """
        :param ledger_path: path to ledger to import
        :type ledger_store: usawa.LedgerStore
        """
        self.db = ValkeyStore('')
        self.client = unix_client
        self.ledger_path = ledger_path
    
    
    def _init_store(self) -> tuple[LedgerStore, Ledger, DemoWallet]:
        """Initialize a fresh LedgerStore, Ledger, and Wallet for each operation."""
        ledger_tree = load(self.ledger_path)
        ledger = Ledger.from_tree(ledger_tree)
        store = LedgerStore(self.db, ledger)

        pk = store.get_key()
        wallet = DemoWallet(privatekey=pk)
        logg.debug("wallet pk: %s pubk: %s", wallet.privkey().hex(), wallet.pubkey().hex())

        ledger.set_wallet(wallet)
        ledger.acl = ACL.from_wallet(wallet)
        store.load(acl=ledger.acl)

        return store, ledger, wallet

    def save(self, domain_entry: LedgerEntry) -> bool:
        """Save a domain entry to storage"""
        try:
            store, ledger, wallet = self._init_store()
            ledger.truncate()

            logg.debug("serial after load : %s", ledger.serial)

            entry = EntryMapper.to_entry(domain_entry, ledger=ledger)
            entry.sign(wallet)
            logg.debug(f"Mapped entry - Serial: {entry.serial}, Parent: {entry.parent.hex()}")

            store.add_entry(entry, update_ledger=True)

            ledger.truncate()
            ledger.sign()

            logg.debug("Parent digest after add_entry %s", self._get_parent_digest().hex())
            return True
        except Exception:
            logg.exception("Failed to save entry")
            return False

    def get_all_entries(self) -> List[LedgerEntry]:
        """Get all entries"""
        try:
            store, _, _ = self._init_store()

            return [
                EntryMapper.to_domain_entry(storage_entry)
                for _, storage_entry in store.ledger.entries.items()
            ]
        except Exception as e:
            logg.error(f"Failed to retrieve entries: {e}")
            return []