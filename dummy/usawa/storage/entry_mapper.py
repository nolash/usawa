import logging
from datetime import datetime, date

from usawa.asset import Asset
from usawa.entry import Entry, EntryPart
from usawa.unit import UnitIndex
from ..core.models import LedgerEntry
from usawa import Entry, EntryPart

logg = logging.getLogger("storage.entry_mapper")


class EntryMapper:
    """Maps between domain model (LedgerEntry) and storage model (Entry)"""
    
    @staticmethod
    def to_entry(domain: LedgerEntry, ledger, unitindex=None):
        """
        Convert LedgerEntry (domain) to Entry (storage)
        
        :param domain: Domain model entry
        :type domain: LedgerEntry
        :param ledger: The ledger object (for parent digest)
        :type ledger: usawa.Ledger
        :param unitindex: UnitIndex for validation
        :type unitindex: UnitIndex
        :return: Storage model entry
        :rtype: Entry
        """
        
        
        if domain.tx_date is None:
            raise ValueError("Transaction date is required for storage")
        
    
        tx_date = domain.tx_date
        if isinstance(tx_date, date) and not isinstance(tx_date, datetime):
            tx_date = datetime.combine(tx_date, datetime.min.time())
        
        
        parent = ledger.current() if ledger else None
        ref = domain.transaction_ref if domain.transaction_ref else None

        entry = Entry(
            serial= ledger.peek(),
            tx_date=tx_date,
            parent=parent,  
            description=domain.description or "",
            ref=ref,  
            unitindex = UnitIndex('BTC')
        )
        
        source_amount = domain.amount
        source_part = EntryPart(
            "BTC",
            domain.source_type.lower(),
            domain.source_path,
            source_amount,
            debit=True
        )
        entry.add_part(source_part, debit=True)
        
        
        dest_amount = -domain.amount
        dest_part = EntryPart(
            "BTC",
            domain.dest_type.lower(),
            domain.dest_path,
            dest_amount,
            debit=False 
        )
        entry.add_part(dest_part, debit=False)
    
        logg.debug(f"Mapped entry, serial: {entry.serial} parent: {entry.parent}")
        return entry
    
    @staticmethod
    def to_domain_entry(storage_entry) -> LedgerEntry:
        """
        Convert Entry (storage) to LedgerEntry (domain)
        
        :param storage_entry: Storage model entry
        :type storage_entry: Entry
        :return: Domain model entry
        :rtype: LedgerEntry
        """
        
        # Extract debit (source) information
        source_unit = ""
        source_type = ""
        source_path = ""
        amount = 0.0
        
        if storage_entry.debit:
            debit_part = storage_entry.debit[0]
            source_unit = debit_part.unit
            source_type = debit_part.category
            source_path = debit_part.account
            amount = abs(float(debit_part.value))
        
        # Extract credit (destination) information
        dest_unit = ""
        dest_type = ""
        dest_path = ""
        
        if storage_entry.credit:
            credit_part = storage_entry.credit[0]
            dest_unit = credit_part.unit
            dest_type = credit_part.category
            dest_path = credit_part.account
        
        # Convert parent digest to hex string if bytes
        parent_digest = None
        if storage_entry.parent:
            if isinstance(storage_entry.parent, bytes):
                parent_digest = storage_entry.parent.hex()
            else:
                parent_digest = str(storage_entry.parent)
        
        tx_date = storage_entry.dt
        date_registered = storage_entry.dtreg
        

        transaction_ref = str(storage_entry.ref) if storage_entry.ref else None
        
        
        external_ref = None
        description = storage_entry.description
        
        
        domain = LedgerEntry(
            external_reference=external_ref,
            description=description,
            amount=amount,
            source_unit=source_unit,
            source_type=source_type,
            source_path=source_path,
            dest_unit=dest_unit,
            dest_type=dest_type,
            dest_path=dest_path,
            attachments=storage_entry.attachment.copy() if storage_entry.attachment else [],
            serial=storage_entry.serial,
            tx_date=tx_date,
            date_registered=date_registered,
            transaction_ref=transaction_ref,
            parent_digest=parent_digest,
            unit_index=storage_entry.uidx
        )
        
        logg.debug(f"Mapped storage entry #{storage_entry.serial} to domain LedgerEntry")
        return domain