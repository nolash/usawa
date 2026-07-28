from datetime import datetime
import logging
from gi.repository import Gtk, Adw, Gio, Pango
from pathlib import Path
import mimetypes
from usawa.gui.core.models import EntryPartData

logg = logging.getLogger("gui.create_entry_view")


def create_entry_page(ctx, nav_view, controller, account_list=None):
    page = Adw.NavigationPage(title="Create New Entry", tag="create-entry")

    view = CreateEntryView(ctx, nav_view, controller, account_list=account_list)
    page.set_child(view)
    return page


class CreateEntryView(Gtk.Box):

    def __init__(self, ctx, nav_view, controller, account_list=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.ctx = ctx
        self.nav_view = nav_view
        self.controller = controller
        self.account_list = account_list
        self.attachment_paths: list[str] = []

        self._build_ui(nav_view)

    def _build_ui(self, nav_view):
        header = self._create_header(nav_view=nav_view)
        self.append(header)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_top(16)
        content.set_margin_bottom(16)
        content.set_margin_start(16)
        content.set_margin_end(16)

        # Sections
        basic_section = self._create_basic_section()
        content.append(basic_section)

        transaction_section = self._create_transaction_section()
        content.append(transaction_section)

        tags_section = self._create_tags_section()
        content.append(tags_section)

        attachments_section = self._create_attachments_section()
        content.append(attachments_section)

        warning = self._create_warning()
        content.append(warning)

        scrolled.set_child(content)
        self.append(scrolled)

        action_bar = self._create_action_bar()
        self.append(action_bar)

    def _create_header(self, nav_view):
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header_box.set_margin_top(12)
        header_box.set_margin_bottom(12)
        header_box.set_margin_start(12)
        header_box.set_margin_end(12)

        back_btn = Gtk.Button()
        back_btn.set_icon_name("go-previous-symbolic")
        back_btn.add_css_class("flat")
        back_btn.connect("clicked", lambda b: nav_view.pop())
        header_box.append(back_btn)

        title = Gtk.Label(label="Create new Entry")
        title.add_css_class("title-2")
        header_box.append(title)

        serial_badge = Gtk.Label(
            label=f"Next Serial: #{self.controller.next_serial():04d}"
        )
        serial_badge.add_css_class("caption")
        serial_badge.add_css_class("accent")
        serial_badge.set_margin_start(8)
        serial_badge.set_margin_end(8)
        serial_badge.set_margin_top(4)
        serial_badge.set_margin_bottom(4)
        header_box.append(serial_badge)
        return header_box

    def _create_basic_section(self):
        section_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        header = Gtk.Label(label="BASIC DETAILS")
        header.set_halign(Gtk.Align.START)
        header.add_css_class("heading")
        section_box.append(header)

        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(12)

        ref_label = Gtk.Label(label="External reference (optional)")
        ref_label.set_halign(Gtk.Align.START)
        ref_label.add_css_class("dim-label")
        grid.attach(ref_label, 0, 0, 2, 1)

        self.ref_entry = Gtk.Entry()
        self.ref_entry.set_hexpand(True)
        grid.attach(self.ref_entry, 0, 1, 2, 1)

        desc_label = Gtk.Label(label="Description (optional)")
        desc_label.set_halign(Gtk.Align.START)
        desc_label.add_css_class("dim-label")
        grid.attach(desc_label, 0, 2, 2, 1)

        self.desc_entry = Gtk.Entry()
        self.desc_entry.set_placeholder_text("Brief description of the entry")
        self.desc_entry.set_hexpand(True)
        grid.attach(self.desc_entry, 0, 3, 2, 1)

        section_box.append(grid)
        return section_box

    def _create_transaction_section(self):
        """Create transaction details section with per-side currencies"""
        section_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        header = Gtk.Label(label="TRANSACTION DETAILS")
        header.set_halign(Gtk.Align.START)
        header.add_css_class("heading")
        section_box.append(header)

        # Transaction date
        date_label = Gtk.Label(label="Transaction Date")
        date_label.set_halign(Gtk.Align.START)
        date_label.add_css_class("dim-label")
        section_box.append(date_label)

        date_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self.date_entry = Gtk.Entry()
        self.date_entry.set_placeholder_text("YYYY-MM-DD")
        self.date_entry.set_text(datetime.now().strftime("%Y-%m-%d"))
        self.date_entry.set_hexpand(True)
        date_box.append(self.date_entry)

        calendar_btn = Gtk.Button()
        calendar_btn.set_icon_name("x-office-calendar-symbolic")
        calendar_btn.add_css_class("flat")
        calendar_btn.connect("clicked", self._on_show_calendar)
        date_box.append(calendar_btn)
        section_box.append(date_box)

        # Optional time
        time_label = Gtk.Label(label="Transaction Time (optional)")
        time_label.set_halign(Gtk.Align.START)
        time_label.add_css_class("dim-label")
        section_box.append(time_label)

        self.time_entry = Gtk.Entry()
        self.time_entry.set_placeholder_text("H:MM or H:MM:SS")
        section_box.append(self.time_entry)

        # Amount
        amount_label = Gtk.Label(label="Amount")
        amount_label.set_halign(Gtk.Align.START)
        amount_label.add_css_class("dim-label")
        section_box.append(amount_label)

        self.amount_entry = Gtk.Entry()
        self.amount_entry.set_placeholder_text("0.00")
        section_box.append(self.amount_entry)

        # Source / Destination cards
        ledger_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        ledger_box.set_homogeneous(True)

        source_card = self._create_ledger_side_card("Source", is_source=True)
        ledger_box.append(source_card)

        dest_card = self._create_ledger_side_card("Destination", is_source=False)
        ledger_box.append(dest_card)

        section_box.append(ledger_box)

        return section_box

    def _create_tags_section(self):
        """Create the tags section with add/remove chip-style widget."""
        section_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        header = Gtk.Label(label="TAGS")
        header.set_halign(Gtk.Align.START)
        header.add_css_class("heading")
        section_box.append(header)

        self.tags_flow = Gtk.FlowBox()
        self.tags_flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.tags_flow.set_max_children_per_line(8)
        self.tags_flow.set_row_spacing(6)
        self.tags_flow.set_column_spacing(6)
        section_box.append(self.tags_flow)

        input_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self.tag_input = Gtk.Entry()
        self.tag_input.set_placeholder_text("Add tag…")
        self.tag_input.set_hexpand(True)
        self.tag_input.connect("activate", self._on_tag_input_activate)
        input_row.append(self.tag_input)

        add_tag_btn = Gtk.Button()
        add_tag_btn.set_icon_name("list-add-symbolic")
        add_tag_btn.set_tooltip_text("Add tag")
        add_tag_btn.connect("clicked", self._on_tag_add_clicked)
        input_row.append(add_tag_btn)

        section_box.append(input_row)

        self.tags = []

        return section_box

    def _on_tag_add_clicked(self, button):
        self._commit_tag_input()

    def _on_tag_input_activate(self, entry_widget):
        self._commit_tag_input()

    def _commit_tag_input(self):
        text = self.tag_input.get_text().strip()
        if not text:
            return
        if text in self.tags:
            self.tag_input.set_text("")
            return
        self._add_tag_chip(text)
        self.tag_input.set_text("")

    def _create_attachments_section(self):
        """Create the attachments section"""
        section_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        header = Gtk.Label(label="ATTACHMENTS")
        header.set_halign(Gtk.Align.START)
        header.add_css_class("heading")
        section_box.append(header)

        attachments_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        attachments_card.add_css_class("card")
        attachments_card.set_margin_top(8)
        attachments_card.set_margin_bottom(8)
        attachments_card.set_margin_start(8)
        attachments_card.set_margin_end(8)

        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header_box.set_margin_top(8)
        header_box.set_margin_start(8)
        header_box.set_margin_end(8)

        attach_label = Gtk.Label(label="Add supporting Documents")
        attach_label.set_halign(Gtk.Align.START)
        attach_label.set_hexpand(True)
        header_box.append(attach_label)

        add_btn = Gtk.Button()
        add_btn.set_icon_name("list-add-symbolic")
        add_btn.set_label("Add File")
        add_btn.add_css_class("flat")
        add_btn.connect("clicked", self.on_add_attachment)
        header_box.append(add_btn)

        attachments_card.append(header_box)

        self.attachment_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.attachment_list.set_margin_start(8)
        self.attachment_list.set_margin_end(8)
        self.attachment_list.set_margin_bottom(8)

        attachments_card.append(self.attachment_list)

        section_box.append(attachments_card)

        return section_box

    def _create_attachment_row(self, filename: str, file_path: str, metadata: str):
        """Create a single attachment row"""
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.add_css_class("card")
        row.set_margin_top(4)
        row.set_margin_bottom(4)
        row.set_margin_start(4)
        row.set_margin_end(4)

        row.file_path = file_path

        icon = self._get_icon_for_file(filename, metadata)
        row.append(icon)

        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_box.set_hexpand(True)

        name_label = Gtk.Label(label=filename)
        name_label.set_halign(Gtk.Align.START)
        name_label.add_css_class("caption")
        name_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        info_box.append(name_label)

        meta_label = Gtk.Label(label=metadata)
        meta_label.set_halign(Gtk.Align.START)
        meta_label.add_css_class("dim-label")
        meta_label.add_css_class("caption")
        info_box.append(meta_label)

        row.append(info_box)

        remove_btn = Gtk.Button(label="Remove")
        remove_btn.add_css_class("destructive-action")
        remove_btn.connect("clicked", lambda b: self._on_remove_attachment(row))
        row.append(remove_btn)

        return row

    def _create_ledger_side_card(self, title, is_source=True):
        """Create a card for source or destination, supporting multiple entry parts."""
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card.add_css_class("card")
        card.set_margin_top(8)
        card.set_margin_bottom(8)
        card.set_margin_start(8)
        card.set_margin_end(8)

        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header_box.set_margin_top(8)
        header_box.set_margin_start(8)
        header_box.set_margin_end(8)

        header = Gtk.Label(label=title)
        header.set_halign(Gtk.Align.START)
        header.add_css_class("heading")
        header.set_hexpand(True)
        header_box.append(header)

        add_btn = Gtk.Button()
        add_btn.set_icon_name("list-add-symbolic")
        add_btn.add_css_class("flat")
        header_box.append(add_btn)
        card.append(header_box)

        entry_parts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        entry_parts.set_margin_start(8)
        entry_parts.set_margin_end(8)
        card.append(entry_parts)

        sum_label = Gtk.Label()
        sum_label.set_halign(Gtk.Align.START)
        sum_label.add_css_class("dim-label")
        sum_label.add_css_class("caption")
        sum_label.set_margin_start(8)
        sum_label.set_margin_bottom(8)
        card.append(sum_label)

        if is_source:
            self.source_rows = []
            self.source_container = entry_parts
            self.source_sum_label = sum_label
        else:
            self.dest_rows = []
            self.dest_container = entry_parts
            self.dest_sum_label = sum_label

        add_btn.connect("clicked", lambda b: self._add_entry_part_row(is_source))
        self._add_entry_part_row(is_source)

        return card

    def _get_side_state(self, is_source):
        if is_source:
            return self.source_rows, self.source_container, self.source_sum_label
        return self.dest_rows, self.dest_container, self.dest_sum_label

    def _add_entry_part_row(self, is_source):
        rows, parts_list, sum_label = self._get_side_state(is_source)

        row_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        row_box.add_css_class("card")
        row_box.set_margin_bottom(4)

        row_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row_header.set_margin_top(6)
        row_header.set_margin_start(6)
        row_header.set_margin_end(6)

        row_title = Gtk.Label(label=f"Part {len(rows) + 1}")
        row_title.add_css_class("caption")
        row_title.add_css_class("dim-label")
        row_title.set_hexpand(True)
        row_title.set_halign(Gtk.Align.START)
        row_header.append(row_title)

        remove_btn = Gtk.Button()
        remove_btn.set_icon_name("list-remove-symbolic")
        remove_btn.add_css_class("flat")
        row_header.append(remove_btn)
        row_box.append(row_header)

        fields = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        fields.set_margin_start(6)
        fields.set_margin_end(6)
        fields.set_margin_bottom(6)

        units = Gtk.StringList()
        for sym in self.ctx.store.ledger.uidx.syms():
            units.append(sym)
        unit_dropdown = Gtk.DropDown(model=units)
        unit_dropdown.set_selected(0)
        unit_dropdown.connect(
            "notify::selected", lambda d, p: self._update_sum_label(is_source)
        )
        fields.append(unit_dropdown)

        types = Gtk.StringList()
        type_order = (
            ["Expense", "Asset", "Liability", "Income"]
            if is_source
            else ["Asset", "Expense", "Liability", "Income"]
        )
        for t in type_order:
            types.append(t)
        type_dropdown = Gtk.DropDown(model=types)
        fields.append(type_dropdown)

        path_entry = Gtk.Entry()
        path_entry.set_placeholder_text("Account path")
        path_entry.set_text("general")
        fields.append(path_entry)

        amount_entry = Gtk.Entry()
        amount_entry.set_placeholder_text("Amount")
        amount_entry.connect("changed", lambda e: self._update_sum_label(is_source))
        fields.append(amount_entry)

        row_box.append(fields)
        parts_list.append(row_box)

        row_data = {
            "box": row_box,
            "unit_dropdown": unit_dropdown,
            "type_dropdown": type_dropdown,
            "path_entry": path_entry,
            "amount_entry": amount_entry,
        }
        rows.append(row_data)
        remove_btn.connect(
            "clicked", lambda b: self._remove_part_row(is_source, row_data)
        )
        self._update_sum_label(is_source)

    def _remove_part_row(self, is_source, row_data):
        rows, parts_list, sum_label = self._get_side_state(is_source)
        if len(rows) <= 1:
            return  # keep at least one part per side
        rows.remove(row_data)
        parts_list.remove(row_data["box"])
        self._update_sum_label(is_source)

    def _update_sum_label(self, is_source):
        rows, parts_list, sum_label = self._get_side_state(is_source)

        totals = {}
        for row in rows:
            unit_item = row["unit_dropdown"].get_selected_item()
            unit = unit_item.get_string() if unit_item else None
            amount_text = row["amount_entry"].get_text().strip()
            try:
                amount = float(amount_text) if amount_text else 0.0
            except ValueError:
                amount = 0.0
            if unit:
                totals[unit] = totals.get(unit, 0.0) + amount

        if not totals:
            sum_label.set_text("= —")
        else:
            parts_str = "  ·  ".join(f"{v:g} {k}" for k, v in totals.items())
            sum_label.set_text(f"= {parts_str}")

    def _rows_to_entry_parts(self, rows) -> list:
        uidx = self.ctx.store.ledger.uidx
        parts = []

        for i, row in enumerate(rows, start=1):
            unit_item = row["unit_dropdown"].get_selected_item()
            type_item = row["type_dropdown"].get_selected_item()
            unit = unit_item.get_string() if unit_item else None
            acc_type = type_item.get_string() if type_item else None
            path = row["path_entry"].get_text().strip()
            amount_text = row["amount_entry"].get_text().strip()

            if not unit or not acc_type or not path or not amount_text:
                raise ValueError(f"Part {i}: all fields are required")

            try:
                amount = uidx.from_floatstring(unit, amount_text)
            except (ValueError, KeyError) as e:
                raise ValueError(
                    f"Part {i}: invalid amount '{amount_text}' for unit {unit}"
                ) from e

            parts.append(
                EntryPartData(
                    unit=unit,
                    account_type=acc_type,
                    account_path=path,
                    amount=amount,
                )
            )

        return parts

    def get_source_entry_parts(self) -> list:
        return self._rows_to_entry_parts(self.source_rows)

    def get_dest_entry_parts(self) -> list:
        return self._rows_to_entry_parts(self.dest_rows)

    def _create_warning(self):
        """Create warning note"""
        warning = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        warning.add_css_class("card")
        warning.add_css_class("warning")
        warning.set_margin_top(8)
        warning.set_margin_bottom(8)
        warning.set_margin_start(8)
        warning.set_margin_end(8)

        icon = Gtk.Image.new_from_icon_name("dialog-warning-symbolic")
        warning.append(icon)

        text = Gtk.Label()
        text.set_markup(
            "<b>Note:</b> Entries cannot be saved as drafts. You must either Finalize or Discard."
        )
        text.set_wrap(True)
        text.set_hexpand(True)
        text.set_halign(Gtk.Align.START)
        warning.append(text)

        return warning

    def _create_action_bar(self):
        """Create action bar with buttons"""
        action_bar = Gtk.ActionBar()

        discard_btn = Gtk.Button(label="Discard")
        discard_btn.add_css_class("destructive-action")
        discard_btn.connect("clicked", self._on_discard)
        action_bar.pack_start(discard_btn)

        finalize_btn = Gtk.Button(label="Finalize Entry")
        finalize_btn.add_css_class("suggested-action")
        finalize_btn.connect("clicked", self._on_finalize)
        action_bar.pack_end(finalize_btn)

        return action_bar

    def get_source_unit(self) -> str:
        """Get selected source unit"""
        selected_idx = self.source_unit_dropdown.get_selected()
        model = self.source_unit_dropdown.get_model()
        return model.get_string(selected_idx)

    def get_source_type(self) -> str:
        """Get selected source type"""
        selected_idx = self.source_type_dropdown.get_selected()
        model = self.source_type_dropdown.get_model()
        return model.get_string(selected_idx)

    def get_dest_unit(self) -> str:
        """Get selected dest unit"""
        selected_idx = self.dest_unit_dropdown.get_selected()
        model = self.dest_unit_dropdown.get_model()
        return model.get_string(selected_idx)

    def get_dest_type(self) -> str:
        """Get selected dest type"""
        selected_idx = self.dest_type_dropdown.get_selected()
        model = self.dest_type_dropdown.get_model()
        return model.get_string(selected_idx)

    def _on_discard(self, button):
        """Handle discard button"""
        self.nav_view.pop()

    def on_add_attachment(self, button):
        """Handle add attachment button - multiple files"""
        logg.info("Add attachment clicked")

        file_dialog = Gtk.FileDialog()
        file_dialog.set_title("Select Attachments")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        all_filter = Gtk.FileFilter()
        all_filter.set_name("All Files")
        all_filter.add_pattern("*")
        filters.append(all_filter)
        file_dialog.set_filters(filters)

        file_dialog.open_multiple(
            parent=self.get_root(), callback=self._on_files_selected
        )

    def _on_files_selected(self, dialog, result):
        try:
            files = dialog.open_multiple_finish(result)

            if files:
                for i in range(files.get_n_items()):
                    file = files.get_item(i)
                    file_path = file.get_path()
                    logg.info(f"File selected: {file_path}")
                    self.attachment_paths.append(file_path)
                    self._add_attachment_to_list(file_path)

        except Exception as e:
            logg.debug(f"File selection cancelled or failed: {e}")

    def _get_icon_for_file(self, filename: str, metadata: str):
        """Get appropriate icon for file type"""
        icon_name = "text-x-generic-symbolic"

        if "pdf" in metadata.lower():
            icon_name = "application-pdf-symbolic"
        elif "image" in metadata.lower():
            icon_name = "image-x-generic-symbolic"
        elif "text" in metadata.lower():
            icon_name = "text-x-generic-symbolic"
        elif "video" in metadata.lower():
            icon_name = "video-x-generic-symbolic"
        elif "audio" in metadata.lower():
            icon_name = "audio-x-generic-symbolic"

        icon = Gtk.Image.new_from_icon_name(icon_name)
        return icon

    def _add_attachment_to_list(self, file_path: str):
        path = Path(file_path)

        filename = path.name
        file_size = path.stat().st_size
        mime_type, _ = mimetypes.guess_type(file_path)

        if mime_type is None:
            mime_type = "application/octet-stream"

        size_str = self._format_file_size(file_size)

        attachment_row = self._create_attachment_row(
            filename=filename, file_path=file_path, metadata=f"{mime_type} • {size_str}"
        )

        self.attachment_list.append(attachment_row)
        logg.info(f"Added attachment: {filename} ({size_str})")

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable form"""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def _on_finalize(self, button):

        try:
            source_parts = self.get_source_entry_parts()
            dest_parts = self.get_dest_entry_parts()
        except ValueError as e:
            self._show_error_dialog("Invalid Input", str(e))
            return

        tags = self.get_tags()

        entry = self.controller.collect_entry_data(
            self, source_parts, dest_parts, tags, self.attachment_paths
        )
        if entry is None:
            self._show_error_dialog(
                "Invalid Input", "Please check your entries and try again."
            )
            return

        if entry.attachments:
            for attachment_path in entry.attachments:
                if not Path(attachment_path).exists():
                    self._show_error_dialog(
                        "Attachment Missing",
                        f"Attachment file not found: {Path(attachment_path).name}",
                    )
                    return

        success, error_msg = self.controller.finalize_entry(entry)

        if success:
            self.controller.notify_entry_created()
            logg.info("Entry saved successfully, returning to list")
            self.nav_view.pop()
        else:
            self._show_error_dialog("Save Failed", error_msg)

    def _show_error_dialog(self, title, message):
        dialog = Adw.MessageDialog(
            transient_for=self.get_root(), heading=title, body=message
        )
        dialog.add_response("ok", "OK")
        dialog.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", lambda d, response: d.close())

        dialog.present()

    def _on_remove_attachment(self, row):
        file_path = row.file_path

        if file_path in self.attachment_paths:
            self.attachment_paths.remove(file_path)

        parent = row.get_parent()
        if parent is not None:
            parent.remove(row)
        logg.debug("Removed attachment: %s", file_path)

    def _on_show_calendar(self, button):
        popover = Gtk.Popover()
        popover.set_parent(button)

        calendar = Gtk.Calendar()
        calendar.connect("day-selected", lambda c: self._on_date_selected(c, popover))
        popover.set_child(calendar)
        popover.popup()

    def _on_date_selected(self, calendar, popover):
        date = calendar.get_date()
        date_str = f"{date.get_year():04d}-{date.get_month():02d}-{date.get_day_of_month():02d}"
        self.date_entry.set_text(date_str)
        popover.popdown()

    def _on_tag_input_activate(self, entry_widget):
        text = entry_widget.get_text().strip()
        if not text:
            return
        if text in self.tags:
            entry_widget.set_text("")
            return
        self._add_tag_chip(text)
        entry_widget.set_text("")

    def _add_tag_chip(self, tag_text):
        self.tags.append(tag_text)

        chip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        chip.add_css_class("card")
        chip.set_margin_top(2)
        chip.set_margin_bottom(2)
        chip.set_margin_start(4)
        chip.set_margin_end(4)

        label = Gtk.Label(label=tag_text)
        label.set_margin_start(8)
        label.set_margin_top(4)
        label.set_margin_bottom(4)
        chip.append(label)

        remove_btn = Gtk.Button()
        remove_btn.set_icon_name("window-close-symbolic")
        remove_btn.add_css_class("flat")
        remove_btn.set_margin_end(4)
        chip.append(remove_btn)

        flow_child = Gtk.FlowBoxChild()
        flow_child.set_child(chip)
        self.tags_flow.append(flow_child)

        remove_btn.connect(
            "clicked", lambda b: self._remove_tag_chip(tag_text, flow_child)
        )

    def _remove_tag_chip(self, tag_text, flow_child):
        if tag_text in self.tags:
            self.tags.remove(tag_text)
        self.tags_flow.remove(flow_child)

    def get_tags(self) -> list:
        return list(self.tags)
