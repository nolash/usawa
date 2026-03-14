import hashlib
import logging
from typing import List
from usawa.core.usawa_wallet import UsawaWallet
import hexathon
from usawa.storage.xml_utils import (
    _build_export_root,
    _build_incoming_element,
    _find_child,
    _find_entry_by_serial,
    _write_xml_to_file,
    resolve_namespace,
)
from usawa.asset import Asset
from usawa.crypto import ACL, DemoWallet, Wallet
from usawa.error import VerifyError
from usawa.ledger import Ledger
from usawa.resolve.fs import FSResolver
from usawa.service import UnixClient
from usawa.store import LedgerStore
from ..core.models import LedgerEntry
from .entry_mapper import EntryMapper
from whee.valkey import ValkeyStore
from usawa import Ledger, DemoWallet, load
from pathlib import Path
import mimetypes
import lxml.etree as ET
from pathlib import Path
import lxml.etree as ET
from copy import deepcopy


logg = logging.getLogger("storage.ledger_repository")


# def sha256_verify(k, v=None):
#     if isinstance(k, str):
#         k = bytes.fromhex(k)

#     if len(k) != 32:
#         raise ValueError("expect 256 bit key")

#     khx = hexathon.uniform(k.hex())

#     if v is not None:
#         h = hashlib.sha256()
#         h.update(v)
#         if k != h.digest():
#             raise VerifyError(khx)

#     return khx


class LedgerRepository:
    """Repository that wraps LedgerStore and handles mapping"""

    wallet_class = DemoWallet

    def __init__(
        self,
        ledger_path=None,
        unix_client: UnixClient = None,
        valkey_store: ValkeyStore = None,
        cfg=None,
        wallet=None,
    ):
        """
        Initialize the LedgerRepository.

        :param ledger_path: Path to the ledger definition file to import.
        :type ledger_path: str | None

        :param unix_client: Unix socket client used to communicate with the storage service.
        :type unix_client: usawa.UnixClient

        """
        self.valkey_store = valkey_store
        self.unix_client = unix_client
        self._wallet = wallet
        self._store = None
        self.ledger_path = ledger_path
        self.cfg = cfg
        self.resolver = FSResolver(self.cfg.get("FS_RESOLVER_STORE_PATH"))

    def _init_store(self, write=False) -> tuple[LedgerStore, Ledger, Wallet]:
        ledger_tree = load(self.ledger_path)
        ledger = Ledger.from_tree(ledger_tree)

        if write:
            logg.info("init store for write")
            self.store = LedgerStore(self.valkey_store, ledger)
            if self._wallet is not None:
                try:
                    self.store.get_key(wallet_class=UsawaWallet)
                    logg.info("wallet already in store, skipping add_key")
                except FileNotFoundError:
                    logg.info("persisting wallet to store")
                    self.store.add_key(self._wallet)
            else:
                try:
                    logg.info("retrieving wallet from store")
                    self._wallet = self.store.get_key(wallet_class=UsawaWallet)
                    logg.info(
                        "wallet ready, pubkey: %s...", self._wallet.pubkey().hex()[:16]
                    )
                except FileNotFoundError:
                    logg.warning("no wallet found in store — import required")
                    self._wallet = None
        else:
            logg.info("init store for read")
            self.store = LedgerStore(self.valkey_store, ledger)
            if self._wallet is not None:
                try:
                    self.store.get_key(wallet_class=UsawaWallet)
                except FileNotFoundError:
                    logg.info("persisting wallet to store")
                    self.store.add_key(self._wallet)

        logg.info("wallet ready, pubkey: %s...", self._wallet.pubkey().hex()[:16])

        ledger.set_wallet(self._wallet)
        ledger.acl = ACL.from_wallet(self._wallet)
        self.store.load(acl=ledger.acl)
        return self.store, ledger, self._wallet

    def save(self, domain_entry: LedgerEntry) -> None:
        """
        Save a domain entry to storage

        :param domain_entry: Entry to save
        :type domain_entry: LedgerEntry
        :raises ValueError: If validation fails
        :raises FileExistsError: If attachment already exists in the store
        :raises IOError: If file operations fail
        :raises Exception: For other storage errors
        """
        try:
            store, ledger, wallet = self._init_store(write=True)

            entry = EntryMapper.to_entry(domain_entry, ledger=ledger)
            entry.sign(wallet)

            logg.debug(
                "Mapped entry - Serial: %s, Parent: %s, Attachments: %s",
                entry.serial,
                entry.parent.hex(),
                entry.attachment,
            )

            for attachment in domain_entry.attachments:
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

            store.add_entry(entry, update_ledger=True)

            ledger.truncate()
            ledger.sign()
            logg.info(f"Successfully saved entry #{entry.serial}")

        except FileExistsError as e:
            logg.debug(f"Entry fileinfo already exists: {e}")
            raise
        except ValueError as e:
            logg.debug(f"Validation error: {e}")
            raise
        except IOError as e:
            logg.debug(f"File operation failed: {e}")
            raise
        except Exception as e:
            logg.debug(f"Failed to save entry: {e}", exc_info=True)
            raise

    def save_wallet(self, wallet):
        """Persist wallet to store so it can be retrieved on subsequent launches."""
        ledger_tree = load(self.ledger_path)
        ledger = Ledger.from_tree(ledger_tree)
        self.store = LedgerStore(self.valkey_store, ledger)
        self.store.add_key(wallet)
        logg.info(
            "wallet persisted to store, pubkey: %s...", wallet.pubkey().hex()[:16]
        )

    def get_all_entries(self) -> List[LedgerEntry]:
        """Get all entries"""
        try:
            store, _, _ = self._init_store()

            return [
                EntryMapper.to_domain_entry(storage_entry)
                for _, storage_entry in store.ledger.entries.items()
            ]
        except Exception as e:
            # logg.error(f"Failed to retrieve entries: {e}")
            logg.error("failed to map entries: %s", e, exc_info=True)
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
            ledger = self.store.ledger

            tree = ledger.to_tree()
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            xml_string = ET.tostring(
                tree, encoding="utf-8", xml_declaration=True, pretty_print=True
            )

            with open(output_file, "wb") as f:
                f.write(xml_string)

            logg.info(f"Exported ledger to {output_path}")
            return True, ""

        except PermissionError as e:
            error_msg = "Permission denied. Cannot write to the specified location."
            logg.debug(f"Permission error: {e}")
            return False, error_msg

        except IOError as e:
            error_msg = f"Failed to write file: {str(e)}"
            logg.debug(f"I/O error: {e}")
            return False, error_msg

        except Exception as e:
            error_msg = f"Failed to export ledger: {str(e)}"
            logg.debug("Unexpected error during export")
            return False, error_msg

    def export_entry_to_xml(self, serial: int, output_path: str) -> tuple[bool, str]:
        try:
            storage_entry = self.store.ledger.entries.get(serial)
            if not storage_entry:
                return False, f"Entry #{serial} not found"

            xml_tree = self.store.ledger.to_tree()
            ns_uri = resolve_namespace(xml_tree)
            target_entry = _find_entry_by_serial(xml_tree, ns_uri, serial)
            if target_entry is None:
                return False, f"Entry #{serial} not found in XML"

            incoming = _build_incoming_element(ns_uri, target_entry, xml_tree)
            root = _build_export_root(xml_tree, ns_uri, target_entry, incoming)
            _write_xml_to_file(root, output_path)
            self.store.ledger.truncate()
            logg.debug(
                "Ledger entries after truncate: %d", len(self.store.ledger.entries)
            )
            self.resolver.put_entry(entry=storage_entry, lookup="sha512")

            logg.info(f"Successfully exported entry #{serial} -> {output_path}")
            return True, ""

        except PermissionError:
            return False, "Permission denied"
        except IOError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)
