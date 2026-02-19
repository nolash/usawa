import logging
from typing import Optional

from usawa.core.entry_service import EntryService
from ...core.models import LedgerEntry

logg = logging.getLogger("gui.entry_controller")


class EntryController:

    """Handles entry creation logic"""
    def __init__(self,entry_service: EntryService):
        self.entry_service = entry_service
       
    def collect_entry_data(self, view) -> Optional[LedgerEntry]:
        """Collect data from the view and create an entry"""
        try:
            entry = LedgerEntry(
                external_reference=view.ref_entry.get_text().strip() or None,
                description=view.desc_entry.get_text().strip() or None,
                amount=float(view.amount_entry.get_text() or "0"),
                source_unit="BTC",
                source_type=view.get_source_type(),
                source_path=view.source_path_entry.get_text().strip(),
                dest_unit="BTC",
                dest_type=view.get_dest_type(),
                dest_path=view.dest_path_entry.get_text().strip(),
            )
  
            is_valid, error_msg = entry.validate()
            if not is_valid:
                logg.error(f"Validation failed: {error_msg}")
                return None 
            return entry
            
        except ValueError as e:
            logg.error(f"Failed to collect entry data: {e}")
            return None
    
    def finalize_entry(self, entry: LedgerEntry) -> bool:
        """Save the entry to the ledger"""
        try:
            logg.debug("Entry: %s", entry)
            success = self.entry_service.save_entry(entry)
            if success:
                logg.info(f"Entry saved successfully")
            else:
                logg.error("Failed to save entry")
            return True
        except Exception as e:
            logg.error(f"Failed to save entry: {e}")
            return False