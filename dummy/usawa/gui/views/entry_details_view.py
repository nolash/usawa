import logging
import threading
from gi.repository import Gtk, Adw,Pango,Gdk,GdkPixbuf,GLib
import threading
import tempfile
import subprocess
import logging

logg = logging.getLogger("gui.entry_details_view")


def create_entry_details_page(entry, nav_view,fetch_fn):
    """Create an entry details page for the navigation stack"""
    page = Adw.NavigationPage(
        title="Entry Details",
        tag=f"entry-{entry.serial}"
    )
    view = EntryDetailsView(entry, nav_view,fetch_fn)
    page.set_child(view)
    return page


class EntryDetailsView(Gtk.Box):
    """Entry details view"""

    def __init__(self, entry, nav_view,fetch_fn):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.entry = entry
        self.nav_view = nav_view
        self.fetch_fn = fetch_fn 
        self._build_ui()

    def _build_ui(self):
        self.append(self._create_header())

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content.set_margin_top(20)
        content.set_margin_bottom(20)
        content.set_margin_start(20)
        content.set_margin_end(20)

        content.append(self._create_entry_details_section())
        content.append(self._create_transaction_section())
        content.append(self._create_attachments_section())

        scrolled.set_child(content)
        self.append(scrolled)

    def _create_header(self):
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header_box.set_margin_top(12)
        header_box.set_margin_bottom(12)
        header_box.set_margin_start(12)
        header_box.set_margin_end(12)
        header_box.add_css_class("toolbar")

        back_btn = Gtk.Button()
        back_btn.set_icon_name("go-previous-symbolic")
        back_btn.add_css_class("flat")
        back_btn.connect("clicked", lambda b: self.nav_view.pop())
        header_box.append(back_btn)

        return header_box

    def _create_entry_details_section(self):
        section_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        header = Gtk.Label(label="ENTRY DETAILS")
        header.set_halign(Gtk.Align.START)
        header.add_css_class("heading")
        section_box.append(header)

        grid = Gtk.Grid()
        grid.set_column_spacing(16)
        grid.set_row_spacing(12)
        grid.set_column_homogeneous(True)

        _add_field_to_grid(grid, "Serial number", str(self.entry.serial), 0, 0)
        _add_field_to_grid(grid, "Transaction reference(uuid)", self.entry.tx_ref, 0, 1)
        _add_field_to_grid(grid, "Transaction date", self.entry.tx_date, 1, 0)
        _add_field_to_grid(grid, "Date registered", self.entry.tx_date_rg.strftime("%Y-%m-%d %H:%M:%S") if self.entry.tx_date_rg else "", 1, 1)

        parent_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        parent_label = Gtk.Label(label="Parent Digest")
        parent_label.set_halign(Gtk.Align.START)
        parent_label.add_css_class("dim-label")
        parent_label.add_css_class("caption")
        parent_box.append(parent_label)

        parent_value = Gtk.Label(label=self.entry.parent_digest)
        parent_value.set_halign(Gtk.Align.START)
        parent_value.set_selectable(True)
        parent_value.set_wrap(False)
        parent_value.set_ellipsize(Pango.EllipsizeMode.END)
        parent_value.set_max_width_chars(70)
        parent_value.add_css_class("monospace")
        parent_box.append(parent_value)

        grid.attach(parent_box, 0, 2, 2, 1)
        signer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        signer_label = Gtk.Label(label="Signers")
        signer_label.set_halign(Gtk.Align.START)
        signer_label.add_css_class("dim-label")
        signer_label.add_css_class("caption")
        signer_box.append(signer_label)

        signers = self.entry.signers_raw

        if len(signers) == 1:
            pubkey = signers[0]
            short_key = f"{pubkey[:8]}...{pubkey[-6:]}"
            
            signer_value = Gtk.Label(label=short_key)
            signer_value.set_halign(Gtk.Align.START)
            signer_value.set_selectable(True)
            signer_value.set_tooltip_text(pubkey)
            signer_value.add_css_class("monospace")
            
            signer_box.append(signer_value)

        elif len(signers) > 1:
            expander = Gtk.Expander(label=f"{len(signers)} signers")

            key_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

            for pubkey in signers:
                short_key = f"{pubkey[:8]}...{pubkey[-6:]}"
                key_label = Gtk.Label(label=short_key)
                key_label.set_halign(Gtk.Align.START)
                key_label.set_selectable(True)
                key_label.set_tooltip_text(pubkey)
                key_label.add_css_class("monospace")
                key_list.append(key_label)

            expander.set_child(key_list)
            signer_box.append(expander)
        else:
              none_label = Gtk.Label(label="No signatures")
              none_label.set_halign(Gtk.Align.START)
              signer_box.append(none_label)
        grid.attach(signer_box, 0, 3, 1, 1)

        auth_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        auth_label = Gtk.Label(label="Authentication State")
        auth_label.set_halign(Gtk.Align.START)
        auth_label.add_css_class("dim-label")
        auth_label.add_css_class("caption")
        auth_box.append(auth_label)

        auth_badge = _create_auth_badge(self.entry.auth_state)
        auth_badge.set_halign(Gtk.Align.START)
        auth_box.append(auth_badge)
        grid.attach(auth_box, 1, 3, 1, 1)

        desc_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        desc_label = Gtk.Label(label="Description")
        desc_label.set_halign(Gtk.Align.START)
        desc_label.add_css_class("dim-label")
        desc_label.add_css_class("caption")
        desc_box.append(desc_label)

        desc_value = Gtk.Label(label=self.entry.description)
        desc_value.set_halign(Gtk.Align.START)
        desc_value.set_wrap(True)
        desc_box.append(desc_value)
        grid.attach(desc_box, 0, 4, 2, 1)

        section_box.append(grid)
        return section_box

    def _create_transaction_section(self):
        section_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        header = Gtk.Label(label="TRANSACTION DETAILS")
        header.set_halign(Gtk.Align.START)
        header.add_css_class("heading")
        section_box.append(header)

        amount_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        amount_label = Gtk.Label(label="Amount")
        amount_label.set_halign(Gtk.Align.START)
        amount_label.add_css_class("dim-label")
        amount_label.add_css_class("caption")
        amount_box.append(amount_label)

        amount_value = Gtk.Label(label=self.entry.amount)
        amount_value.set_halign(Gtk.Align.START)
        amount_value.add_css_class("title-1")
        amount_box.append(amount_value)
        section_box.append(amount_box)

        ledger_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        ledger_box.set_homogeneous(True)

        logg.debug("Created EntryItem in TX Section: %s", self.entry)

        ledger_box.append(_create_ledger_card(
            "Source",
            self.entry.source_unit,
            self.entry.source_type,
            self.entry.source_path,
            is_source=True
        ))
        ledger_box.append(_create_ledger_card(
            "Destination",
            self.entry.dest_unit,
            self.entry.dest_type,
            self.entry.dest_path,
            is_source=False
        ))

        section_box.append(ledger_box)
        return section_box

    def _create_attachments_section(self):
        section_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        header = Gtk.Label(label="ATTACHMENTS")
        header.set_halign(Gtk.Align.START)
        header.add_css_class("heading")
        section_box.append(header)

        attachments_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        if self.entry.attachments_raw:
            for asset in self.entry.attachments_raw:
                attach_card = _create_attachment_card(
                    asset.slug or "Unnamed",
                    asset.mime or "unknown",
                    on_click=lambda f, a=asset: _open_attachment_viewer(
                        self.get_root(),
                        a,
                        fetch_fn=self.fetch_fn
                    )
                )
                attachments_box.append(attach_card)

        section_box.append(attachments_box)
        return section_box


def _add_field_to_grid(grid, label_text, value_text, row, col):
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
    value.set_selectable(True)
    field_box.append(value)

    grid.attach(field_box, col, row, 1, 1)


def _create_auth_badge(auth_state):
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

    header = Gtk.Label(label=title)
    header.set_halign(Gtk.Align.START)
    header.add_css_class("heading")
    header.set_margin_top(8)
    header.set_margin_start(8)
    card.append(header)

    fields_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    fields_box.set_margin_start(8)
    fields_box.set_margin_end(8)
    fields_box.set_margin_bottom(8)

    _add_label_value_pair(fields_box, "Account Unit:", unit)
    _add_label_value_pair(fields_box, "Account Type:", account_type)
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


def _create_attachment_card(filename, metadata, on_click=None):
    """Create an attachment card"""
    card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    card.add_css_class("card")
    card.set_margin_top(8)
    card.set_margin_bottom(8)
    card.set_size_request(200, -1)

    if on_click:
        gesture = Gtk.GestureClick.new()
        gesture.connect("pressed", lambda gesture, n_press, x, y: on_click(filename))
        card.add_controller(gesture)
        card.set_cursor(Gdk.Cursor.new_from_name("pointer"))

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

    meta_label = Gtk.Label(label=metadata)
    meta_label.set_halign(Gtk.Align.START)
    meta_label.add_css_class("dim-label")
    meta_label.add_css_class("caption")
    meta_label.set_margin_start(12)
    meta_label.set_margin_bottom(12)
    card.append(meta_label)

    return card

def _open_attachment_viewer(parent_window, asset, fetch_fn):
    """Fetch bytes in a background thread then open the appropriate viewer."""


    def on_fetched(bytes_data):
        if bytes_data is None:
            _show_error_dialog(parent_window, "Failed to load attachment", "Could not retrieve asset data for {}.".format(asset.slug))
            return

        mime = asset.mime or ""
        if mime.startswith("image/"):
            _show_image_viewer(parent_window, asset.slug, bytes_data)
        elif mime == "application/pdf":
            _show_pdf_viewer(parent_window, asset.slug, bytes_data)
        elif mime.startswith("text/") or mime in ("application/json", "application/xml"):
            _show_text_viewer(parent_window, asset.slug, bytes_data)
        else:
            _show_unsupported_dialog(parent_window, asset.slug, mime)

    threading.Thread(
        target=lambda: GLib.idle_add(on_fetched, fetch_fn(asset.digest)),
        daemon=True
    ).start()


def _show_image_viewer(parent, title, data):
    dialog = Gtk.Window(title=title)
    dialog.set_transient_for(parent)
    dialog.set_modal(True)
    dialog.set_default_size(800, 600)

    loader = GdkPixbuf.PixbufLoader()
    loader.write(data)
    loader.close()
    pixbuf = loader.get_pixbuf()

    scroll = Gtk.ScrolledWindow()
    image = Gtk.Picture.new_for_pixbuf(pixbuf)
    image.set_content_fit(Gtk.ContentFit.CONTAIN)
    scroll.set_child(image)
    dialog.set_child(scroll)
    dialog.present()


def _show_text_viewer(parent, title, data):
    dialog = Gtk.Window(title=title)
    dialog.set_transient_for(parent)
    dialog.set_modal(True)
    dialog.set_default_size(800, 600)

    scroll = Gtk.ScrolledWindow()
    text_view = Gtk.TextView()
    text_view.set_editable(False)
    text_view.set_monospace(True)
    text_view.get_buffer().set_text(data.decode("utf-8", errors="replace"))
    scroll.set_child(text_view)
    dialog.set_child(scroll)
    dialog.present()


def _show_pdf_viewer(parent, title, data):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(data)
        tmp_path = f.name
    subprocess.Popen(["evince", tmp_path])


def _show_unsupported_dialog(parent, filename, mime):
    dialog = Gtk.AlertDialog()
    dialog.set_message(f"Cannot preview '{filename}'")
    dialog.set_detail(f"No viewer available for type: {mime}")
    dialog.show(parent)


def _show_error_dialog(self, title, message):
    dialog = Adw.MessageDialog(
        transient_for=self.get_root(),
        heading=title,
        body=message
    )
    dialog.add_response("ok", "OK")
    dialog.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
    dialog.connect("response", lambda d, response: d.close())
    
    dialog.present()