import logging
from datetime import datetime
import uuid

from .models import LedgerEntry
from usawa.storage.ledger_repository import LedgerRepository

logg = logging.getLogger("core.entry_service")


class EntryService:

    def __init__(self, repository: LedgerRepository):
        self.repository = repository

    def save_entry(self, entry: LedgerEntry) -> tuple[bool, str]:
        entry.date_registered = datetime.now()
        entry.transaction_ref = str(uuid.uuid4())

        is_valid, error_msg = entry.validate()
        if not is_valid:
            logg.error(f"Entry validation failed: {error_msg}")
            return False, error_msg

        try:
            self.repository.save(entry)
        except (FileExistsError, ValueError, IOError, Exception) as e:
            error_msg = self._error_message_for(e)
            logg.error(
                f"Save failed: {e}",
                exc_info=not isinstance(e, (FileExistsError, ValueError, IOError)),
            )
            return False, error_msg

        logg.info("Entry saved successfully")
        return True, ""

    def _error_message_for(self, e: Exception) -> str:
        if isinstance(e, FileExistsError):
            return (
                "Some file information for this entry is already recorded in the ledger"
            )
        if isinstance(e, ValueError):
            return f"Invalid entry data: {e}"
        if isinstance(e, IOError):
            return f"File error: {e}"
        return f"Failed to save entry: {e}"

    def get_all_entries(self):
        return self.repository.get_all_entries()

    def get_asset_bytes(self, digest: bytes) -> bytes:
        return self.repository.get_asset_bytes(digest=digest)

    def export_all_entries_to_xml(self, output_path: str) -> tuple[bool, str]:
        return self.repository.export_all_entries_to_xml(output_path=output_path)

    def export_entry_to_xml(self, serial: int, output_path: str) -> tuple[bool, str]:
        return self.repository.export_entry_to_xml(serial, output_path)
