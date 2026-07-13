import logging
from datetime import datetime, date

from usawa.entry import Entry, EntryPart
from usawa.ledger import Ledger
from usawa.account import Account
from usawa.unit import UnitIndex
from ..gui.core.models import LedgerEntry
from usawa import Entry, EntryPart

logg = logging.getLogger("storage.entry_mapper")


class EntryMapper:
    """Maps between domain model (LedgerEntry) and storage model (Entry)"""

    @staticmethod
    def to_entry(domain: LedgerEntry, ledger):
        if domain.tx_date is None:
            raise ValueError("Transaction date is required for storage")

        tx_date = domain.tx_date
        if isinstance(tx_date, date) and not isinstance(tx_date, datetime):
            tx_date = datetime.combine(tx_date, datetime.min.time())

        unitindex = UnitIndex(base=domain.dest_unit)

        parent = ledger.current() if ledger else None
        ref = domain.transaction_ref if domain.transaction_ref else None

        entry = Entry(
            serial=ledger.next_serial(),
            tx_date=tx_date,
            parent=parent,
            description=domain.description or "",
            ref=ref,
            unitindex=UnitIndex(domain.dest_unit),
        )

        source_amount = unitindex.from_floatstring(unitindex.base, str(domain.amount))
        dest_amount = -source_amount

        account = Account(
            unitindex.base, domain.source_type.lower(), domain.source_path
        )
        source_part = EntryPart(
            account,
            source_amount,
            debit=True,
        )
        entry.add_part(source_part)

        account = Account(unitindex.base, domain.dest_type.lower(), domain.dest_path)
        dest_part = EntryPart(
            account,
            dest_amount,
            debit=False,
        )
        entry.add_part(dest_part)

        return entry

    @staticmethod
    def to_domain_entry(ledger: Ledger, storage_entry: Entry) -> LedgerEntry:
        """
        Convert Entry (storage) to LedgerEntry (domain)
        """

        base = ledger.uidx.base
        precision = ledger.uidx.detail[base]

        source_unit = ""
        source_type = ""
        source_path = ""
        amount = 0.0

        dest_unit = ""
        dest_type = ""
        dest_path = ""
        if storage_entry.debit:
            debit_part = storage_entry.debit[0]
            source_unit = debit_part.get_unit()
            source_type = debit_part.get_type()
            source_path = debit_part.account_path_only()
            amount = abs(float(debit_part.amount))
        else:
            source_unit = source_type = source_path = ""
            amount = 0.0

        if storage_entry.credit:
            credit_part = storage_entry.credit[0]
            dest_unit = credit_part.get_unit()
            dest_type = credit_part.get_type()
            dest_path = credit_part.account_path_only()
        else:
            dest_unit = dest_type = dest_path = ""

        parent_digest = parent_digest = storage_entry.parent.hex()

        tx_date = storage_entry.dt
        date_registered = storage_entry.dtreg

        external_ref = None

        signer_pubkeys = list(storage_entry.sigs.keys())

        domain = LedgerEntry(
            external_reference=external_ref,
            description=storage_entry.description,
            amount=amount,
            precision=precision,
            source_unit=source_unit,
            source_type=source_type,
            source_path=source_path,
            dest_unit=dest_unit,
            dest_type=dest_type,
            dest_path=dest_path,
            attachments=(
                storage_entry.attachment.copy() if storage_entry.attachment else []
            ),
            serial=storage_entry.serial,
            tx_date=tx_date,
            tx_reference=storage_entry.ref,
            date_registered=date_registered,
            signer_pubkeys=signer_pubkeys,
            parent_digest=parent_digest,
            unit_index=storage_entry.uidx,
        )

        return domain
