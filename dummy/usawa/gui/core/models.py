from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
from pathlib import Path


@dataclass
class LedgerEntry:
    """DTO for ledger entry input, converted to usawa.Entry before adding to ledger."""

    # Basic details
    external_reference: Optional[str] = None
    description: Optional[str] = None

    # Transaction details
    amount: float = 0.0
    source_unit: str = ""
    source_type: str = ""
    source_path: str = "general"
    dest_unit: str = ""
    dest_type: str = ""
    dest_path: str = "general"

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
        if self.amount <= 0:
            return False, "Amount must be greater than 0"

        if not self.source_unit or not self.dest_unit:
            return False, "Unit/Currency is required for both source and destination"

        if not self.source_type or not self.dest_type:
            return False, "Account type is required for both source and destination"

        if not self.source_path or not self.dest_path:
            return False, "Account path is required for both source and destination"

        # Validate attachments
        if self.attachments:
            for filepath in self.attachments:
                if not Path(filepath).exists():
                    return False, f"Attachment file not found: {filepath}"

        return True, ""
