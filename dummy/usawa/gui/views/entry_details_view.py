import logging
from gi.repository import Gtk, Adw,Pango

logg = logging.getLogger("gui.entry_details")

def create_entry_details_page(entry,nav_view):
    """Create an entry details page for the navigation stack"""
    
    # Create navigation page
    page = Adw.NavigationPage(
        title="Entry Details",
        tag=f"entry-{entry.serial}"
    )

    main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        
    header = _create_header(nav_view)
    main_box.append(header)
        

    scrolled = Gtk.ScrolledWindow()
    scrolled.set_vexpand(True)
    scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    
    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
    content.set_margin_top(20)
    content.set_margin_bottom(20)
    content.set_margin_start(20)
    content.set_margin_end(20)
    
    # Entry Details Section
    entry_details = _create_entry_details_section(entry)
    content.append(entry_details)
    
    # Transaction Details Section
    transaction_details = _create_transaction_section(entry)
    content.append(transaction_details)
    
    # Attachments Section
    attachments_section = _create_attachments_section(entry)
    content.append(attachments_section)
    
    scrolled.set_child(content)
    main_box.append(scrolled)  
    page.set_child(main_box)
    
    return page


def _create_header(nav_view):
    """Create header with back button and serial badge"""
    header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    header_box.set_margin_top(12)
    header_box.set_margin_bottom(12)
    header_box.set_margin_start(12)
    header_box.set_margin_end(12)
    header_box.add_css_class("toolbar")
      
    back_btn = Gtk.Button()
    back_btn.set_icon_name("go-previous-symbolic")
    back_btn.set_label("Back to List")
    back_btn.add_css_class("flat")
    back_btn.connect("clicked", lambda b: nav_view.pop())
    header_box.append(back_btn)
    header_box.append(back_btn)
    
    serial_badge = Gtk.Label(label=f"#{"0001"}")
    serial_badge.add_css_class("accent")
    serial_badge.add_css_class("caption")
    serial_badge.set_margin_start(8)
    serial_badge.set_margin_end(8)
    serial_badge.set_margin_top(4)
    serial_badge.set_margin_bottom(4)
    header_box.append(serial_badge)
    
    return header_box
    
def _create_entry_details_section(entry):
        """Create the entry metadata section"""
        section_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        
        header = Gtk.Label(label="ENTRY DETAILS")
        header.set_halign(Gtk.Align.START)
        header.add_css_class("heading")
        section_box.append(header)
        

        grid = Gtk.Grid()
        grid.set_column_spacing(16)
        grid.set_row_spacing(12)
        grid.set_column_homogeneous(True)
        

        _add_field_to_grid(grid, "Serial number", str(entry.serial), 0, 0)
        _add_field_to_grid(grid, "Transaction reference(uuid)", 
                               entry.tx_ref, 0, 1)
        _add_field_to_grid(grid, "Transaction date", entry.tx_date, 1, 0)
        _add_field_to_grid(grid, "Date registered", entry.tx_date_rg, 1, 1)

        parent_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        parent_label = Gtk.Label(label="Parent Digest")
        parent_label.set_halign(Gtk.Align.START)
        parent_label.add_css_class("dim-label")
        parent_label.add_css_class("caption")
        parent_box.append(parent_label)

        parent_value = Gtk.Label(
            label=entry.parent_digest
        )
        parent_value.set_halign(Gtk.Align.START)
        parent_value.set_selectable(True)  
        parent_value.set_wrap(False)  
        parent_value.set_ellipsize(Pango.EllipsizeMode.END) 
        parent_value.set_max_width_chars(70)  
        parent_value.add_css_class("monospace")
        parent_box.append(parent_value)

        grid.attach(parent_box, 0, 2, 2, 1)
        _add_field_to_grid(grid, "Unix Index", "1707665400", 3, 0)

        
        # Auth state with badge
        auth_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        auth_label = Gtk.Label(label="Authentication State")
        auth_label.set_halign(Gtk.Align.START)
        auth_label.add_css_class("dim-label")
        auth_label.add_css_class("caption")
        auth_box.append(auth_label)
        
        auth_badge = _create_auth_badge(entry.auth_state)
        auth_badge.set_halign(Gtk.Align.START)
        auth_box.append(auth_badge)
        
        
        grid.attach(auth_box, 1, 3, 1, 1)
        
        
        desc_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        desc_label = Gtk.Label(label="Description")
        desc_label.set_halign(Gtk.Align.START)
        desc_label.add_css_class("dim-label")
        desc_label.add_css_class("caption")
        desc_box.append(desc_label)
        
        desc_value = Gtk.Label(label=entry.description)
        desc_value.set_halign(Gtk.Align.START)
        desc_value.set_wrap(True)
        desc_box.append(desc_value)
        
        grid.attach(desc_box, 0, 4, 2, 1)
        
        section_box.append(grid)
        
        return section_box
    
def _create_transaction_section(entry):
    """Create the transaction details section"""
    section_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    
    # Section header
    header = Gtk.Label(label="TRANSACTION DETAILS")
    header.set_halign(Gtk.Align.START)
    header.add_css_class("heading")
    section_box.append(header)
    
    # Amount field
    amount_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    amount_label = Gtk.Label(label="Amount")
    amount_label.set_halign(Gtk.Align.START)
    amount_label.add_css_class("dim-label")
    amount_label.add_css_class("caption")
    amount_box.append(amount_label)
    
    amount_value = Gtk.Label(label="0.045")
    amount_value.set_halign(Gtk.Align.START)
    amount_value.add_css_class("title-1")
    amount_box.append(amount_value)
    
    section_box.append(amount_box)
    
    # Source and Destination cards
    ledger_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
    ledger_box.set_homogeneous(True)
    
    # Source card
    source_card = _create_ledger_card(
        "Source",
        entry.source_unit,
        entry.source_type,
        entry.source_path,
        is_source=True
    )
    ledger_box.append(source_card)
    
    # Destination card
    dest_card = _create_ledger_card(
        "Destination",
        entry.dest_unit,
        entry.dest_type,
        entry.dest_path,
        is_source=False
    )
    ledger_box.append(dest_card)
    
    section_box.append(ledger_box)
    
    return section_box

def _create_attachments_section(self):
    """Create the attachments section"""
    section_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    
    # Section header
    header = Gtk.Label(label="ATTACHMENTS")
    header.set_halign(Gtk.Align.START)
    header.add_css_class("heading")
    section_box.append(header)
    
    # Attachments container
    attachments_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    
    # Attachment 1
    attach1 = _create_attachment_card(
        "payment_receipt.txt",
        "text/plain • 3 KB"
    )
    attachments_box.append(attach1)
    
    # Attachment 2
    attach2 = _create_attachment_card(
        "payment_receipt.png",
        "image/png • 1.2 MB"
    )
    attachments_box.append(attach2)
    
    section_box.append(attachments_box)
    
    return section_box

def _add_field_to_grid( grid, label_text, value_text, row, col):
    """Helper to add a field to the grid"""
    field_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    
    label = Gtk.Label(label=label_text)
    label.set_halign(Gtk.Align.START)
    label.add_css_class("dim-label")
    label.add_css_class("caption")
    field_box.append(label)
    
    value = Gtk.Label(label=value_text)
    value.set_halign(Gtk.Align.START)
    value.add_css_class("monospace")
    value.set_selectable(True)  # Allow copying
    field_box.append(value)
    
    grid.attach(field_box, col, row, 1, 1)
    
def _create_auth_badge( auth_state):
    """Create an authentication state badge"""
    badge = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
    badge.set_margin_top(4)
    badge.set_margin_bottom(4)
    badge.set_margin_start(8)
    badge.set_margin_end(8)
    badge.add_css_class("badge")
    
    icon = Gtk.Label()
    text = Gtk.Label()
    text.add_css_class("caption")
    
    if auth_state == "trusted":
        badge.add_css_class("auth-trusted")
        icon.set_text("✓")
        text.set_text("Trusted")
    elif auth_state == "not_trusted":
        badge.add_css_class("auth-not-trusted")
        icon.set_text("⚠")
        text.set_text("Not Trusted")
    elif auth_state == "unknown":
        badge.add_css_class("auth-unknown")
        icon.set_text("?")
        text.set_text("Unknown Key")
    elif auth_state == "invalid":
        badge.add_css_class("auth-invalid")
        icon.set_text("✗")
        text.set_text("Invalid")
    else:
        badge.add_css_class("auth-unsigned")
        icon.set_text("○")
        text.set_text("No Key")
    
    badge.append(icon)
    badge.append(text)
    
    return badge
    
def _create_ledger_card(title, unit, account_type, path, is_source=True):
    """Create a source or destination card"""
    card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    card.add_css_class("card")
    card.set_margin_top(8)
    card.set_margin_bottom(8)
    card.set_margin_start(8)
    card.set_margin_end(8)
    
    # Header
    header = Gtk.Label(label=title)
    header.set_halign(Gtk.Align.START)
    header.add_css_class("heading")
    header.set_margin_top(8)
    header.set_margin_start(8)
    card.append(header)
    
    # Fields
    fields_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    fields_box.set_margin_start(8)
    fields_box.set_margin_end(8)
    fields_box.set_margin_bottom(8)
    
    # Account Unit
    _add_label_value_pair(fields_box, "Account Unit:", unit)
    
    # Account Type
    _add_label_value_pair(fields_box, "Account Type:", account_type)
    
    # Account Path
    _add_label_value_pair(fields_box, "Account Path:", path)
    
    card.append(fields_box)
    
    return card
    
def _add_label_value_pair(container, label_text, value_text):
    """Add a label:value pair to a container"""
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    
    label = Gtk.Label(label=label_text)
    label.set_halign(Gtk.Align.START)
    label.add_css_class("dim-label")
    row.append(label)
    
    value = Gtk.Label(label=value_text)
    value.set_halign(Gtk.Align.START)
    value.add_css_class("monospace")
    value.set_hexpand(True)
    row.append(value)
    
    container.append(row)
    
def _create_attachment_card( filename, metadata):
    """Create an attachment card"""
    card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    card.add_css_class("card")
    card.set_margin_top(8)
    card.set_margin_bottom(8)
    card.set_size_request(200, -1)
    
    # Icon and filename
    header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    header_box.set_margin_top(12)
    header_box.set_margin_start(12)
    header_box.set_margin_end(12)
    
    icon = Gtk.Image.new_from_icon_name("text-x-generic-symbolic")
    header_box.append(icon)
    
    name_label = Gtk.Label(label=filename)
    name_label.set_halign(Gtk.Align.START)
    name_label.add_css_class("caption")
    name_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
    header_box.append(name_label)
    
    card.append(header_box)
    
    # Metadata
    meta_label = Gtk.Label(label=metadata)
    meta_label.set_halign(Gtk.Align.START)
    meta_label.add_css_class("dim-label")
    meta_label.add_css_class("caption")
    meta_label.set_margin_start(12)
    meta_label.set_margin_bottom(12)
    card.append(meta_label)
    
    return card