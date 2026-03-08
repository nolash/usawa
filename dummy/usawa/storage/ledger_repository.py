import hashlib
import logging
from typing import List
import hexathon
from usawa.asset import Asset
from usawa.crypto import ACL, DemoWallet
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


def sha256_verify(k, v=None):
    if isinstance(k, str):
        k = bytes.fromhex(k)

    if len(k) != 32:
        raise ValueError("expect 256 bit key")

    khx = hexathon.uniform(k.hex())

    if v is not None:
        h = hashlib.sha256()
        h.update(v)
        if k != h.digest():
            raise VerifyError(khx)

    return khx


class LedgerRepository:
    """Repository that wraps LedgerStore and handles mapping"""

    def __init__(
        self,
        ledger_path=None,
        unix_client: UnixClient = None,
        valkey_store: ValkeyStore = None,
        cfg=None,
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
        self._wallet = None
        self._store = None
        self.ledger_path = ledger_path
        self.cfg = cfg
        self.resolver = FSResolver(
            self.cfg.get("FS_RESOLVER_STORE_PATH"), verifier=sha256_verify
        )

    def _init_store(self, write=False) -> tuple[LedgerStore, Ledger, DemoWallet]:
        ledger_tree = load(self.ledger_path)
        ledger = Ledger.from_tree(ledger_tree)

        if write:
            logg.info("init store for write")
            self.store = LedgerStore(self.valkey_store, ledger)
            if self._wallet is None:
                pk = self.store.get_key()
                if pk is None:
                    raise ValueError("No private key found in store")
                self._wallet = DemoWallet(privatekey=pk)
        else:
            logg.info("init store for read")
            self.store = LedgerStore(self.valkey_store, ledger)
            if self._wallet is None:
                try:
                    pk = self.store.get_key()
                    self._wallet = DemoWallet(privatekey=pk)
                    logg.info(
                        f"Loaded wallet, pubkey: {self._wallet.pubkey().hex()[:16]}..."
                    )

                except FileNotFoundError:
                    logg.warning("No private key found in store, generating new wallet")
                    privkey = bytes.fromhex(self.cfg.get("SIGS_DEFAULT_PRIVATE_KEY"))
                    self._wallet = DemoWallet(privatekey=privkey)

                    # Add key to store
                    try:
                        self.store.add_key(wallet=self._wallet)
                        logg.info("Stored new private key successfully")
                    except Exception as e:
                        logg.warning(f"Could not store new key: {e}")

                except Exception as e:
                    raise ValueError(
                        f"Could not retrieve or create private key: {e}"
                    ) from e

        logg.debug(
            "wallet pk: %s pubk: %s",
            self._wallet.privkey().hex(),
            self._wallet.pubkey().hex(),
        )
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
        """
        Export all ledger entries to XML file

        :param output_path: Path where XML file will be saved
        :type output_path: str
        :return: (success, error_message) tuple
        :rtype: tuple[bool, str]
        """
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
        """
        Export a single ledger entry to an XML file
        """
        try:
            logg.debug(f"Requested export for entry serial: {serial}")
            storage_entry = self.store.ledger.entries.get(serial)
            if not storage_entry:
                return False, f"Entry #{serial} not found"

            xml_tree = self.store.ledger.to_tree()
            ns_uri = xml_tree.nsmap.get(None)
            if ns_uri is None:
                if "}" in xml_tree.tag:
                    ns_uri = xml_tree.tag.split("}")[0].strip("{")
                else:
                    # Final fallback
                    ns_uri = "http://usawa.defalsify.org/"

            logg.debug(f"Using namespace: {ns_uri}")
            logg.debug(f"Root tag: {xml_tree.tag}")
            logg.debug(f"Namespace map: {xml_tree.nsmap}")

            all_entries = xml_tree.findall(".//{%s}entry" % ns_uri)
            logg.debug(f"Total entries found in XML: {len(all_entries)}")

            target_entry = None

            for entry_elem in all_entries:
                data_elem = _find_child(entry_elem, "data")

                if data_elem is None:
                    logg.warning(f"Entry without <data> element")
                    continue

                serial_elem = _find_child(data_elem, "serial")

                if serial_elem is None:
                    logg.warning("Entry found with no serial element")
                    continue

                entry_serial = int(serial_elem.text)
                logg.debug(f"Inspecting entry serial: {entry_serial}")

                if entry_serial == serial:
                    target_entry = entry_elem
                    logg.debug(f"Target entry found: {serial}")
                    break

            if target_entry is None:
                return False, f"Entry #{serial} not found in XML"

            root = ET.Element("{%s}ledger" % ns_uri, nsmap={None: ns_uri})
            root.set("version", xml_tree.get("version"))

            for tag in ["topic", "generated", "src", "units", "identity"]:
                elem = _find_child(xml_tree, tag)
                if elem is not None:
                    logg.debug(f"Copying {tag} element")
                    root.append(deepcopy(elem))

            data_elem = _find_child(target_entry, "data")

            if data_elem is None:
                return False, "Target entry has no <data> element"

            debit_elem = _find_child(data_elem, "debit")
            credit_elem = _find_child(data_elem, "credit")

            debit_val = 0
            credit_val = 0

            if debit_elem is not None:
                amount_elem = _find_child(debit_elem, "amount")
                if amount_elem is not None:
                    debit_val = int(amount_elem.text)

            if credit_elem is not None:
                amount_elem = _find_child(credit_elem, "amount")
                if amount_elem is not None:
                    credit_val = int(amount_elem.text)

            expense = -abs(debit_val)
            asset = credit_val

            incoming = ET.Element("{%s}incoming" % ns_uri)
            incoming.set("serial", "0")

            real = ET.SubElement(incoming, "{%s}real" % ns_uri)
            real.set("unit", "BTC")

            ET.SubElement(real, "{%s}income" % ns_uri).text = "0"
            ET.SubElement(real, "{%s}expense" % ns_uri).text = str(expense)
            ET.SubElement(real, "{%s}asset" % ns_uri).text = str(asset)
            ET.SubElement(real, "{%s}liability" % ns_uri).text = "0"

            orig_incoming = _find_child(xml_tree, "incoming")
            if orig_incoming is not None:
                digest = _find_child(orig_incoming, "digest")
                if digest is not None:
                    incoming.append(deepcopy(digest))

                sig = _find_child(orig_incoming, "sig")
                if sig is not None:
                    incoming.append(deepcopy(sig))

            root.append(incoming)

            logg.info(f"Appending entry #{serial} to new ledger")
            root.append(deepcopy(target_entry))

            final_entries = root.findall(".//{%s}entry" % ns_uri)
            logg.info(f"Final XML contains {len(final_entries)} entry(ies)")

            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            xml_string = ET.tostring(
                root,
                encoding="utf-8",
                xml_declaration=True,
                pretty_print=True,
            )

            with open(output_file, "wb") as f:
                f.write(xml_string)

            logg.info(f"Successfully exported entry #{serial} -> {output_path}")

            return True, ""

        except PermissionError as e:
            logg.debug(f"Permission error while exporting entry: {e}")
            return False, "Permission denied"

        except IOError as e:
            logg.debug(f"I/O error: {e}")
            return False, str(e)

        except Exception as e:
            logg.debug("Unexpected error during entry export")
            return False, str(e)


def _get_local_name(element):
    """Extract local name from element tag (without namespace)"""
    tag = element.tag
    return tag.split("}")[-1] if "}" in tag else tag


def _find_child(parent, local_name):
    """Find child element by local name"""
    for child in parent:
        if _get_local_name(child) == local_name:
            return child
    return None
