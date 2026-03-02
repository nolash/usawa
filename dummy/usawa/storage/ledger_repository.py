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
    
    def __init__(self,ledger_path = None, unix_client: UnixClient = None):
        """
        :param ledger_path: path to ledger to import
        :type ledger_store: usawa.LedgerStore
        """
        # self.db = ValkeyStore('')
        self.db = unix_client
        self.client = unix_client
        self.ledger_path = ledger_path
        self.resolver = FSResolver("./assets",verifier=sha256_verify)
    
    
    def _init_store(self) -> tuple[LedgerStore, Ledger, DemoWallet]:
        """Initialize a fresh LedgerStore, Ledger, and Wallet for each operation."""
        ledger_tree = load(self.ledger_path)
        ledger = Ledger.from_tree(ledger_tree)
        store = LedgerStore(self.db, ledger)
        
        pk = store.get_key()
        wallet = DemoWallet(privatekey=pk)
        # store.add_key(wallet=wallet,acl=ledger.acl)

        logg.debug("wallet pk: %s pubk: %s", wallet.privkey().hex(), wallet.pubkey().hex())
        ledger.set_wallet(wallet)
        ledger.acl = ACL.from_wallet(wallet)
        store.load(acl=ledger.acl)

        return store, ledger, wallet

    def save(self, domain_entry: LedgerEntry) -> bool:
        """Save a domain entry to storage"""
        try:
            store, ledger, wallet = self._init_store()
            ledger.truncate()

            entry = EntryMapper.to_entry(domain_entry, ledger=ledger)
            entry.sign(wallet)
            logg.debug(f"Mapped entry - Serial: {entry.serial}, Parent: {entry.parent.hex()}, Attachments: {entry.attachment}")

            for attachment in domain_entry.attachments:
                info = self.get_file_info(attachment)
                asset = Asset.from_file(attachment,slug=info["slug"], description= info["description"],mimetype= info["mimetype"])
                store.add_asset(asset)
                entry.attach(asset)

                with open(attachment, "rb") as f:
                    data = f.read()
                self.resolver.put(asset.get_digest(binary=True), data)

            store.add_entry(entry, update_ledger=True)
            ledger.truncate()
            ledger.sign()
            logg.debug("Parent digest after add_entry %s", ledger.parent.hex())
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
        logg.debug(f"Getting asset for digest:{digest}")
        return self.resolver.get(digest)


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