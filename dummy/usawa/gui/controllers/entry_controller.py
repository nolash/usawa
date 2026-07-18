from datetime import datetime
import logging
from typing import Optional

from ..core.entry_service import EntryService
from ..core.models import LedgerEntry

logg = logging.getLogger("gui.entry_controller")


class EntryController:

    def __init__(self, ctx, entry_service: EntryService):
        self.entry_service = entry_service
        self._entry_created_listeners = []
        self.ctx = ctx

    def collect_entry_data(
        self, view, source_parts, dest_parts
    ) -> Optional[LedgerEntry]:
        tx_date_str = view.date_entry.get_text().strip()
        tx_time_str = view.time_entry.get_text().strip()

        try:
            if tx_time_str:
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
                    try:
                        tx_date = datetime.strptime(f"{tx_date_str} {tx_time_str}", fmt)
                        break
                    except ValueError:
                        continue
                else:
                    logg.error("Invalid time format, use H:MM or H:MM:SS")
                    return None
            else:
                tx_date = datetime.strptime(tx_date_str, "%Y-%m-%d").date()
        except ValueError:
            logg.error("Invalid date/time format")
            return None

        try:
            entry = LedgerEntry(
                serial=self.next_serial(),
                external_reference=view.ref_entry.get_text().strip() or None,
                description=view.desc_entry.get_text().strip() or None,
                tx_date=tx_date,
                source_parts=source_parts,
                dest_parts=dest_parts,
            )
            is_valid, error_msg = entry.validate()
            if not is_valid:
                logg.error(f"Validation failed: {error_msg}")
                return None
            return entry
        except ValueError as e:
            logg.error(f"Failed to collect entry data: {e}")
            return None

    def finalize_entry(self, entry: LedgerEntry) -> tuple[bool, str]:
        logg.debug("Finalizing entry: %s", entry)
        success, error_msg = self.entry_service.save_entry(entry)

        if success:
            return True, ""
        else:
            return False, error_msg

    def get_all_entries(self):
        return self.entry_service.get_all_entries()

    def add_entry_created_listener(self, callback):
        self._entry_created_listeners.append(callback)

    def notify_entry_created(self):
        for callback in self._entry_created_listeners:
            callback()

    def next_serial(self, entries: list | None = None) -> int:
        if entries is None:
            entries = self.get_all_entries()
        return len(entries) + 1

    def get_asset_bytes(self, digest: bytes) -> bytes:
        return self.entry_service.get_asset_bytes(digest=digest)

    def export_ledger(self, output_path: str) -> tuple[bool, str]:
        return self.entry_service.export_all_entries_to_xml(output_path)

    def export_entry(self, serial: int, output_path: str) -> tuple[bool, str]:
        return self.entry_service.export_entry_to_xml(serial, output_path)

    def save_wallet(self, wallet, passphrase):
        return self.entry_service.save_wallet(wallet=wallet, passphrase=passphrase)
