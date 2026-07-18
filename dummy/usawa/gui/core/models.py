from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
from pathlib import Path


@dataclass
class EntryPartData:
    unit: str
    account_type: str
    account_path: str
    amount: int


@dataclass
class LedgerEntry:

    # Basic details
    external_reference: Optional[str] = None
    description: Optional[str] = None

    source_parts: List[EntryPartData] = field(default_factory=list)
    dest_parts: List[EntryPartData] = field(default_factory=list)

    # Attachments
    attachments: List[str] = field(default_factory=list)

    # Signers (public keys)
    signer_pubkeys: List[str] = field(default_factory=list)

    serial: Optional[int] = None
    tx_date: Optional[datetime] = None
    tx_reference: Optional[str] = None
    date_registered: Optional[datetime] = None
    parent_digest: Optional[str] = None
    unit_index: Optional[int] = None

    def validate(self) -> tuple[bool, str]:
        """Validate entry data"""
        if not self.source_parts:
            return False, "At least one source part is required"
        if not self.dest_parts:
            return False, "At least one destination part is required"

        for i, part in enumerate(self.source_parts, start=1):
            if part.amount <= 0:
                return False, f"Source part {i}: amount must be greater than 0"
            if not part.unit:
                return False, f"Source part {i}: unit is required"
            if not part.account_type:
                return False, f"Source part {i}: account type is required"
            if not part.account_path:
                return False, f"Source part {i}: account path is required"

        for i, part in enumerate(self.dest_parts, start=1):
            if part.amount <= 0:
                return False, f"Destination part {i}: amount must be greater than 0"
            if not part.unit:
                return False, f"Destination part {i}: unit is required"
            if not part.account_type:
                return False, f"Destination part {i}: account type is required"
            if not part.account_path:
                return False, f"Destination part {i}: account path is required"

        # Validate attachments
        if self.attachments:
            for filepath in self.attachments:
                if not Path(filepath).exists():
                    return False, f"Attachment file not found: {filepath}"

        return True, ""
