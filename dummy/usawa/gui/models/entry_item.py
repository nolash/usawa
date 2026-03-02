from gi.repository import GObject


class EntryItem(GObject.Object):
    """Data model for a ledger entry"""
    
    serial = GObject.Property(type=int, default=0)
    parent_digest = GObject.Property(type=str, default="")
    tx_date = GObject.Property(type=str, default="")
    tx_ref = GObject.Property(type=str, default="")
    tx_date_ref = GObject.Property(type=str, default="")
    description = GObject.Property(type=str, default="")
    auth_state = GObject.Property(type=str, default="unsigned")
    amount = GObject.Property(type=str, default="")
    source_unit = GObject.Property(type=str, default="")
    source_type = GObject.Property(type=str, default="")
    source_path = GObject.Property(type=str, default="")
    dest_unit = GObject.Property(type=str, default="")
    dest_type = GObject.Property(type=str, default="")
    dest_path = GObject.Property(type=str, default="")
    attachments = GObject.Property(type=str, default="") 
    
    def __init__(self, serial=0,parent_digest = "",tx_date="",tx_date_rg= "",tx_ref ="" ,description="", auth_state="unsigned",
                 amount = "",source_unit="", source_type="", source_path="",
                 dest_unit="", dest_type="", dest_path="",attachments = "",attachments_raw= None):
        super().__init__()
        self.serial = serial
        self.parent_digest = parent_digest
        self.tx_date = tx_date
        self.tx_ref = tx_ref
        self.tx_date_rg = tx_date_rg
        self.description = description
        self.auth_state = auth_state
        self.amount = amount
        self.source_unit = source_unit
        self.source_type = source_type
        self.source_path = source_path
        self.dest_unit = dest_unit
        self.dest_type = dest_type
        self.dest_path = dest_path
        self.attachments = attachments
        self.attachments_raw = attachments_raw or []



    def __repr__(self):
        return (
            f"EntryItem("
            f"serial={self.serial},"
            f"description={self.description},"
            f"source_type={self.source_type}, "
            f"destination_type={self.dest_type}, "
            f"amount_source={self.source_unit}:{self.source_path}, "
            f"amount_dest={self.dest_unit}:{self.dest_path}, "
            f"attachments='{self.attachments}', "
            f"attachments_count={len(self.attachments_raw) if hasattr(self, 'attachments_raw') else 0}"
            f")"
        )