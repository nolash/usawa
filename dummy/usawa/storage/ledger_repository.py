import logging
from typing import List
from usawa.gui.core.models import LedgerEntry
from usawa.asset import Asset
from usawa.crypto import ACL, Wallet
from usawa.ledger import Ledger
from usawa.store import LedgerStore
from .entry_mapper import EntryMapper
from usawa import Ledger, load
from pathlib import Path
import mimetypes
import lxml.etree as ET
from pathlib import Path
import lxml.etree as ET

logg = logging.getLogger("storage.ledger_repository")


class LedgerRepository:

    def __init__(
        self,
        ctx,
    ):
        self.ctx = ctx
        self.resolver = ctx.resolver
        self.wallet = ctx.wallet
        self.store = ctx.store
        self.db = ctx.db
        self.ledger = ctx.ledger
        self.ledger_path = ctx.get("ledger_path")

    def _init_store(self, write=False) -> tuple[LedgerStore, Ledger, Wallet]:
        ledger_tree = load(self.ledger_path)
        ledger = Ledger.from_tree(ledger_tree)

        self.store = LedgerStore(self.db, ledger)

        ledger.set_wallet(self.wallet)
        ledger.acl = ACL.from_wallet(self.wallet)
        self.store.load(acl=ledger.acl)
        return self.store, ledger, self.wallet

    def save(self, domain_entry: LedgerEntry) -> None:
        try:
            store, ledger, wallet = self._init_store(write=True)

            entry = EntryMapper.to_entry(self.ctx, domain_entry, ledger=ledger)
            entry.sign(wallet)

            for attachment in domain_entry.attachments:
                self._attach_file(store, entry, attachment)

            store.add_entry(entry, update_ledger=True)

            ledger.truncate()
            ledger.sign()
            logg.info(f"Successfully saved entry #{entry.serial}")

        except Exception as e:
            logg.debug(f"Failed to save entry: {e}", exc_info=True)
            raise

    def _attach_file(self, store, entry, attachment) -> None:
        try:
            info = self.get_file_info(attachment)
            asset = Asset.from_file(
                attachment,
                slug=info["slug"],
                description=info["description"],
                mimetype=info["mimetype"],
            )
            store.add_asset(asset)
            entry.attach(asset)

            with open(attachment, "rb") as f:
                data = f.read()
            self.resolver.put(asset.get_digest(binary=True), data)

        except FileNotFoundError as e:
            raise IOError(f"Attachment file not found: {attachment}") from e
        except PermissionError as e:
            raise IOError(f"Cannot read attachment file: {attachment}") from e

    def get_all_entries(self) -> List[LedgerEntry]:
        """Get all entries"""
        try:
            store, ledger, _ = self._init_store()
            return [
                EntryMapper.to_domain_entry(ledger=ledger, storage_entry=storage_entry)
                for _, storage_entry in store.ledger.entries.items()
            ]
        except Exception as e:
            logg.error(f"Failed to retrieve entries: {e}")
            return []

    def get_asset_bytes(self, digest: str):
        logg.debug(f"Getting asset for digest: {digest}")
        try:
            return self.resolver.get(digest)
        except Exception as e:
            logg.exception("Failed to get asset for digest %s: %s", digest, e)
            return None

    def get_file_info(self, file_path: str) -> dict:
        path = Path(file_path)

        slug = path.stem

        mimetype, _ = mimetypes.guess_type(file_path)

        if mimetype:
            kind = mimetype.split("/")[0]
            description = f"{kind.capitalize()} file: {path.name}"
        else:
            description = f"File: {path.name}"

        return {
            "slug": slug,
            "description": description,
            "mimetype": mimetype,
        }

    def export_all_entries_to_xml(self, output_path: str) -> tuple[bool, str]:
        try:
            for entry in self.ledger.entries.values():
                self.resolver.put_entry(entry, lookup="sha512")

            tree = self.ledger.to_tree()

            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            xml_string = ET.tostring(
                tree,
                encoding="utf-8",
                xml_declaration=True,
                pretty_print=True,
            )

            with open(output_file, "wb") as f:
                f.write(xml_string)

            logg.info("Exported ledger to %s", output_path)
            return True, ""

        except Exception as e:
            return self._handle_export_error(e)

    def export_entry_to_xml(self, serial: int, output_path: str) -> tuple[bool, str]:
        try:
            storage_entry = self.store.ledger.entries.get(serial)
            if storage_entry is None:
                return False, f"Entry #{serial} not found"

            self.resolver.put_entry(storage_entry, lookup="sha512")

            logg.info("Successfully exported entry #%d", serial)
            return True, ""

        except Exception as e:
            return self._handle_export_error(e)

    def _handle_export_error(self, e: Exception) -> tuple[bool, str]:
        if isinstance(e, PermissionError):
            logg.exception("Permission denied during export")
            return False, "Permission denied. Cannot write to the specified location."

        if isinstance(e, IOError):
            logg.exception("I/O error during export")
            return False, f"Failed to write file: {e}"

        logg.exception("Unexpected error during export")
        return False, f"Failed to export: {e}"
