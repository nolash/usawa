import logging
from datetime import datetime
import uuid

from .models import LedgerEntry
from usawa.storage.ledger_repository import LedgerRepository

logg = logging.getLogger("core.entry_service")


class EntryService:
    """Business logic for ledger entries"""

    def __init__(self, repository: LedgerRepository):
        self.repository = repository

    def save_entry(self, entry: LedgerEntry) -> tuple[bool, str]:
        try:
            entry.tx_date = datetime.now()
            entry.date_registered = datetime.now()
            entry.transaction_ref = self._generate_transaction_ref()

            is_valid, error_msg = entry.validate()
            if not is_valid:
                logg.error(f"Entry validation failed: {error_msg}")
                return False, error_msg

            self.repository.save(entry)

            logg.info(f"Entry saved successfully")
            return True, ""

        except FileExistsError as e:
            error_msg = (
                "Some file information for this entry is already recorded in the ledger"
            )
            return False, error_msg

        except ValueError as e:
            error_msg = f"Invalid entry data: {str(e)}"
            logg.error(f"Validation error: {e}")
            return False, error_msg

        except IOError as e:
            error_msg = f"File error: {str(e)}"
            logg.error(f"File operation failed: {e}")
            return False, error_msg

        except Exception as e:
            error_msg = f"Failed to save entry: {str(e)}"
            logg.error(f"Unexpected error: {e}", exc_info=True)
            return False, error_msg

    def get_all_entries(self):
        return self.repository.get_all_entries()

    def _generate_transaction_ref(self) -> str:
        return str(uuid.uuid4())

    def get_asset_bytes(self, digest: bytes) -> bytes:
        return self.repository.get_asset_bytes(digest=digest)

    def export_all_entries_to_xml(self, output_path: str) -> tuple[bool, str]:
        return self.repository.export_all_entries_to_xml(output_path=output_path)

    def export_entry_to_xml(self, serial: int, output_path: str) -> tuple[bool, str]:
        return self.repository.export_entry_to_xml(serial, output_path)
