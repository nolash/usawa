from dataclasses import dataclass,field
from typing import Optional,List, Union
from datetime import datetime
from pathlib import Path

@dataclass
class LedgerEntry:
    """Ledger entry data model"""
    
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

    # Attachmentments
    attachments: List[str] = field(default_factory=list)
    
    # Metadata (auto-generated)
    serial: Optional[int] = None
    tx_date: Optional[datetime] = None
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
    
    def __repr__(self):
        return (
            f"LedgerEntry("
            f"external_reference={self.external_reference!r}, "
            f"description={self.description!r}, "
             f"serial={self.serial!r}, "
            f"amount={self.amount}, "
            f"source_unit={self.source_unit}, "
            f"source_type={self.source_type}, "
            f"dest_unit={self.dest_unit}, "
            f"dest_type={self.dest_type})"
            f"attachments={self.attachments!r})"
        )
    
    def add_attachment(self, filepath: Union[str, List[str]]):
        """
        Add one or more attachment file paths
        """
        if isinstance(filepath, str):
            if filepath not in self.attachments:
                self.attachments.append(filepath)
        elif isinstance(filepath, list):
            for path in filepath:
                if path not in self.attachments:
                    self.attachments.append(path)
        else:
            raise TypeError(f"filepath must be str or List[str], got {type(filepath)}")
    
    def remove_attachment(self, filepath: str):
        """Remove an attachment file path"""
        if filepath in self.attachments:
            self.attachments.remove(filepath)
    
    def get_attachment_count(self) -> int:
        """Get number of attachments"""
        return len(self.attachments)
