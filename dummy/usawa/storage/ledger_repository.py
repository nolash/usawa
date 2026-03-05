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


logg = logging.getLogger("storage.ledger_repository")

def sha256_verify(k, v=None):
    if isinstance(k, str):
        k = bytes.fromhex(k)

    if len(k) != 32:
        raise ValueError('expect 256 bit key')

    khx = hexathon.uniform(k.hex())

    if v is not None:
        h = hashlib.sha256()
        h.update(v)
        if k != h.digest():
            raise VerifyError(khx)

    return khx


class LedgerRepository:
    """Repository that wraps LedgerStore and handles mapping"""
    
    def __init__(self,ledger_path = None, unix_client: UnixClient = None,fs_path: str="./assets"):
        """
        Initialize the LedgerRepository.

        :param ledger_path: Path to the ledger definition file to import.
        :type ledger_path: str | None

        :param unix_client: Unix socket client used to communicate with the storage service.
        :type unix_client: usawa.UnixClient

        :param fs_path: Path to the directory where FSResolver stores assets.
        :type fs_path: str
        """
        self.valkey_store = ValkeyStore('')
        self.unix_client = unix_client
        self._wallet = None
        self._store = None
        self.ledger_path = ledger_path
        self.resolver = FSResolver(fs_path,verifier=sha256_verify)



    def _init_store(self, write=False) -> tuple[LedgerStore, Ledger, DemoWallet]:
        ledger_tree = load(self.ledger_path)
        ledger = Ledger.from_tree(ledger_tree)
        
        if write:
            logg.debug("init store for write")
            self.store = LedgerStore(self.valkey_store, ledger)
            if self._wallet is None:
                pk = self.store.get_key()
                self._wallet = DemoWallet(privatekey=pk)
        else:
            logg.debug("init store for read")
            self.store = LedgerStore(self.valkey_store, ledger)
            if self._wallet is None:
                pk = self.store.get_key()
                self._wallet = DemoWallet(privatekey=pk)

        logg.debug("wallet pk: %s pubk: %s", self._wallet.privkey().hex(), self._wallet.pubkey().hex())
        ledger.set_wallet(self._wallet)
        ledger.acl = ACL.from_wallet(self._wallet)
        self.store.load(acl=ledger.acl)
        return self.store, ledger, self._wallet
    

    def save(self, domain_entry: LedgerEntry) -> bool:
        """Save a domain entry to storage"""
        try:
            store, ledger, wallet = self._init_store(write=True)

            entry = EntryMapper.to_entry(domain_entry, ledger=ledger)
            entry.sign(wallet)
            logg.debug(f"Mapped entry - Serial: {entry.serial}, Parent: {entry.parent.hex()}, Attachments: {entry.attachment}")

            for attachment in domain_entry.attachments:
                info = self.get_file_info(attachment)
                asset = Asset.from_file(attachment,slug=info["slug"], description= info["description"],mimetype= info["mimetype"])
                try:
                    store.add_asset(asset)
                except Exception as e:
                    logg.exception("Failed to add asset for attachment %s: %s", attachment, e)
                    return False

                entry.attach(asset)

                with open(attachment, "rb") as f:
                    data = f.read()
                self.resolver.put(asset.get_digest(binary=True), data)

            store.add_entry(entry, update_ledger=True)
            ledger.truncate()
            ledger.sign()
            return True
        except Exception:
            logg.exception("Failed to save entry")
            return False

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


    def get_file_info(self,file_path: str) -> dict:
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