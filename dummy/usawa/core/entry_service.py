import logging
from datetime import datetime
import uuid

from usawa.service import UnixClient
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
        entry.transaction_ref = self._generate_transaction_ref()
        
        is_valid, error_msg = entry.validate()
        if not is_valid:
            logg.error(f"Entry validation failed: {error_msg}")
            return False
    
        return self.repository.save(entry)
        


    def get_all_entries(self):
        return self.repository.get_all_entries()
    

    
    def _generate_transaction_ref(self) -> str:
        """Generate UUID for transaction"""
        return str(uuid.uuid4())