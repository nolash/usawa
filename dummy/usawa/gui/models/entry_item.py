from gi.repository import GObject


class EntryItem(GObject.Object):
    """Data model for a ledger entry"""

    serial = GObject.Property(type=int, default=0)
    parent_digest = GObject.Property(type=str, default="")
    tx_date = GObject.Property(type=str, default="")
    tx_ref = GObject.Property(type=str, default="")
    tx_date_ref = GObject.Property(type=str, default="")
    description = GObject.Property(type=str, default="")
    auth_state = GObject.Property(type=str, default="")
    source_summary = GObject.Property(type=str, default="")
    dest_summary = GObject.Property(type=str, default="")
    attachments = GObject.Property(type=str, default="")
    signers = GObject.Property(type=str, default="")

    def __init__(
        self,
        serial=0,
        parent_digest="",
        tx_date="",
        tx_date_rg="",
        tx_ref="",
        description="",
        auth_state="unsigned",
        source_summary="",
        dest_summary="",
        source_parts_raw=None,
        dest_parts_raw=None,
        attachments="",
        attachments_raw=None,
        signers="",
        signers_raw=None,
    ):
        super().__init__()
        self.serial = serial
        self.parent_digest = parent_digest
        self.tx_date = tx_date
        self.tx_ref = tx_ref
        self.tx_date_rg = tx_date_rg
        self.description = description
        self.auth_state = auth_state
        self.source_summary = source_summary
        self.dest_summary = dest_summary
        self.source_parts_raw = source_parts_raw or []
        self.dest_parts_raw = dest_parts_raw or []
        self.attachments = attachments
        self.attachments_raw = attachments_raw or []
        self.signers = signers
        self.signers_raw = signers_raw or []
