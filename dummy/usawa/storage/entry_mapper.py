import logging
from datetime import datetime, date

from usawa.entry import Entry, EntryPart
from usawa.ledger import Ledger
from usawa.account import Account
from ..gui.core.models import EntryPartData, LedgerEntry
from usawa import Entry, EntryPart

logg = logging.getLogger("storage.entry_mapper")


class EntryMapper:
    """Maps between domain model (LedgerEntry) and storage model (Entry)"""

    @staticmethod
    def to_entry(ctx, domain: LedgerEntry, ledger):
        if domain.tx_date is None:
            raise ValueError("Transaction date is required for storage")

        tx_date = domain.tx_date
        if isinstance(tx_date, date) and not isinstance(tx_date, datetime):
            tx_date = datetime.combine(tx_date, datetime.min.time())

        parent = ledger.current() if ledger else None
        ref = domain.transaction_ref if domain.transaction_ref else None

        entry = Entry(
            serial=ledger.next_serial(),
            tx_date=tx_date,
            parent=parent,
            description=domain.description or "",
            ref=ref,
            unitindex=ctx.uidx,
        )

        for part_data in domain.source_parts:
            account = Account(
                part_data.unit, part_data.account_type.lower(), part_data.account_path
            )
            entry.add_part(EntryPart(account, part_data.amount, debit=True))

        for part_data in domain.dest_parts:
            account = Account(
                part_data.unit, part_data.account_type.lower(), part_data.account_path
            )
            entry.add_part(EntryPart(account, part_data.amount, debit=False))

        for tag_text in domain.tags:
            entry.tag(tag_text)

        return entry

    @staticmethod
    def to_domain_entry(ledger: Ledger, storage_entry: Entry) -> LedgerEntry:
        """
        Convert Entry (storage) to LedgerEntry (domain)
        """
        source_parts = [
            EntryPartData(
                unit=part.get_unit(),
                account_type=part.get_type(),
                account_path=part.account_path_only(),
                amount=abs(int(part.amount)),
            )
            for part in storage_entry.debit
        ]

        dest_parts = [
            EntryPartData(
                unit=part.get_unit(),
                account_type=part.get_type(),
                account_path=part.account_path_only(),
                amount=abs(int(part.amount)),
            )
            for part in storage_entry.credit
        ]

        parent_digest = storage_entry.parent.hex()

        tx_date = storage_entry.dt
        date_registered = storage_entry.dtreg

        external_ref = None

        signer_pubkeys = list(storage_entry.sigs.keys())

        tags = storage_entry.tags.to_list() if storage_entry.tags else []

        domain = LedgerEntry(
            external_reference=external_ref,
            description=storage_entry.description,
            source_parts=source_parts,
            dest_parts=dest_parts,
            attachments=(
                storage_entry.attachment.copy() if storage_entry.attachment else []
            ),
            serial=storage_entry.serial,
            tx_date=tx_date,
            tags=tags,
            tx_reference=storage_entry.ref,
            date_registered=date_registered,
            signer_pubkeys=signer_pubkeys,
            parent_digest=parent_digest,
            unit_index=ledger.uidx,
        )

        return domain
