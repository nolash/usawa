from gi.repository import Adw, Gtk, Gio,GObject


class EntryItem(GObject.Object):
    """Data model for a ledger entry"""
    
    serial = GObject.Property(type=int, default=0)
    tx_date = GObject.Property(type=str, default="")
    description = GObject.Property(type=str, default="")
    auth_state = GObject.Property(type=str, default="unsigned")
    source_unit = GObject.Property(type=str, default="")
    source_type = GObject.Property(type=str, default="")
    source_path = GObject.Property(type=str, default="")
    dest_unit = GObject.Property(type=str, default="")
    dest_type = GObject.Property(type=str, default="")
    dest_path = GObject.Property(type=str, default="")
    
    def __init__(self, serial=0, tx_date="", description="", auth_state="unsigned",
                 source_unit="", source_type="", source_path="",
                 dest_unit="", dest_type="", dest_path=""):
        super().__init__()
        self.serial = serial
        self.tx_date = tx_date
        self.description = description
        self.auth_state = auth_state
        self.source_unit = source_unit
        self.source_type = source_type
        self.source_path = source_path
        self.dest_unit = dest_unit
        self.dest_type = dest_type
        self.dest_path = dest_path