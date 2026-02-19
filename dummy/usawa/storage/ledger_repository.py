import logging
from typing import Optional, List
from usawa.service import UnixClient
from usawa.store import pfx_entry
from ..core.models import LedgerEntry
from .entry_mapper import EntryMapper

logg = logging.getLogger("storage.ledger_repository")


class LedgerRepository:
    """Repository that wraps LedgerStore and handles mapping"""
    
    def __init__(self, ledger_store,unitindex=None, unix_client: UnixClient = None, wallet=None):
        """
        :param ledger_store: Instance of LedgerStore
        :type ledger_store: usawa.LedgerStore
        """
        self.store = ledger_store
        self.unitindex = unitindex
        self.client = unix_client
        self.wallet = wallet
        self.mapper = EntryMapper()
    
    def save(self, domain_entry: LedgerEntry) -> bool:
        """Save a domain entry to storage"""
        try:
            entry = self.mapper.to_entry(domain_entry, ledger=self.store.ledger)
            logg.debug(f"Mapped entry - Serial: {entry.serial}, Parent: {entry.parent.hex()}")
            entry.sign(self.wallet)
            logg.debug("Ledger current before add_entry: %s", self._get_parent_digest().hex())
            self.store.add_entry(entry, update_ledger=True)
            # self.store.ledger.sign()
            # self.store.load(acl=self.store.ledger.acl)
            logg.debug("Parent digest after add_entry %s", self._get_parent_digest().hex())
            
            return True
            
        except Exception:
            logg.exception("Failed to save entry")
            return False
       

    
    def  get_by_serial(self, serial: int) -> Optional[LedgerEntry]:
        """Get entry by serial number"""
        try:
            storage_entry = self.store.get_entry(serial)
            domain_entry = self.mapper.to_domain_entry(storage_entry)
            
            return domain_entry
            
        except FileNotFoundError:
            logg.warning(f"Entry #{serial} not found")
            return None
        except Exception as e:
            logg.error(f"Failed to retrieve entry #{serial}: {e}")
            return None
        

    def get_next_serial(self) -> int:
        """
        Get the next serial number for a new entry
        
        This calls ledger.next_serial() which:
        1. Increments ledger.serial
        2. Returns the new serial
        
        :return: Next serial number
        :rtype: int
        """
        next_serial = self.store.ledger.peek()
        logg.debug(f"Next serial from ledger.next_serial(): {next_serial}")
        return next_serial

    def _get_parent_digest(self) -> str:
        """Get digest of previous ledger state"""
        return  self.store.ledger.current()
    
    def get_all(self) -> List[LedgerEntry]:
        """Get all entries"""
        try:
            self.store.load()
            domain_entries = []
            for storage_entry in self.store.ledger.entries:
                domain_entry = self.mapper.to_domain_entry(storage_entry)
                domain_entries.append(domain_entry)
            return domain_entries
            
        except Exception as e:
            logg.error(f"Failed to retrieve entries: {e}")
            return []
    
    def get_max_serial(self) -> int:
        """Get highest serial number"""
        return self.store.ledger.serial