import logging
from datetime import datetime
from typing import Optional
import uuid

from usawa.service import UnixClient
from usawa.storage.entry_mapper import EntryMapper
from .models import LedgerEntry
from usawa.storage.ledger_repository import LedgerRepository

logg = logging.getLogger("core.entry_service")


class EntryService:
    """Business logic for ledger entries"""
    
    def __init__(self, repository: LedgerRepository,unixClient: UnixClient):
        self.repository = repository
        self.unix_client = unixClient
    
    def save_entry(self, entry: LedgerEntry) -> bool:
        """
        Save entry with business logic
        
        :param entry: Entry to save
        :type entry: LedgerEntry
        :return: True if saved successfully
        :rtype: bool
        """
    
        entry.tx_date = datetime.now()
        entry.date_registered = datetime.now()
        entry.parent_digest = self._get_parent_digest()
        entry.unit_index = self._get_unit_index()
        entry.transaction_ref = self._generate_transaction_ref()
        entry.serial = self.repository.get_next_serial()
        
        is_valid, error_msg = entry.validate()
        if not is_valid:
            logg.error(f"Entry validation failed: {error_msg}")
            return False
    
        return self.repository.save(entry)
        
    
    def _get_next_serial(self) -> int:
        """Get next serial number"""
        return self.repository.get_max_serial() + 1
    
    def _get_parent_digest(self) -> str:
        """Get digest of previous ledger state"""
        return self.repository._get_parent_digest()
    
    def _get_unit_index(self) -> int:
        """Get Unix timestamp for unit validation"""
        return int(datetime.now().timestamp())
    
    def _generate_transaction_ref(self) -> str:
        """Generate UUID for transaction"""
        return str(uuid.uuid4())