from datetime import date, datetime
import logging
from gi.repository import Gtk, Gio, Pango, GLib

from usawa.gui.models.entry_item import EntryItem
from usawa.gui.views.create_entry_view import create_entry_page
from usawa.gui.views.entry_details_view import create_entry_details_page

logg = logging.getLogger("gui.entrylist")


class EntryListView(Gtk.Box):
    """The entry list view with filters, table, and FAB"""

    def __init__(
        self,
        nav_view,
        entry_controller,
        toast_overlay,
        entries=None,
        refresh_callback=None,
        **kwargs,
    ):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0, **kwargs)

        self.nav_view = nav_view
        self.entry_controller = entry_controller
        self.entries = entries or []
        self.refresh_callback = refresh_callback
        self.toast_overlay = toast_overlay
        self.active_filter = None

        overlay = Gtk.Overlay()
        self.append(overlay)

        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
        )
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)
        overlay.set_child(content)

        # Sort Section
        sort_section = self._create_sort_section()
        content.append(sort_section)

        # Filter Section
        filter_section = self._create_filter_section()
        content.append(filter_section)

        # Table Section
        table_section = self._create_table_section()
        content.append(table_section)

        # Floating Action Button
        fab = Gtk.Button()
        fab.set_icon_name("list-add-symbolic")
        fab.add_css_class("circular")
        fab.add_css_class("suggested-action")
        fab.set_halign(Gtk.Align.END)
        fab.set_valign(Gtk.Align.END)
        fab.set_margin_end(24)
        fab.set_margin_bottom(24)
        overlay.add_overlay(fab)
        fab.connect("clicked", self.on_fab_clicked)

    def _create_sort_section(self):
        """Create the Sort by section with toggle buttons"""
        sort_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        sort_label = Gtk.Label(label="Sort by")
        sort_label.set_halign(Gtk.Align.START)
        sort_label.add_css_class("heading")
        sort_box.append(sort_label)

        button_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        button_container.set_margin_top(4)
        button_container.set_margin_bottom(4)
        button_container.set_margin_start(8)
        button_container.set_margin_end(8)
        button_container.add_css_class("card")

        self.sort_datetime_btn = Gtk.ToggleButton(label="Transaction Datetime")
        self.sort_datetime_btn.set_active(True)
        self.sort_datetime_btn.connect("toggled", self.on_sort_changed, "datetime")
        button_container.append(self.sort_datetime_btn)

        self.sort_serial_btn = Gtk.ToggleButton(label="Serial Number")
        self.sort_serial_btn.connect("toggled", self.on_sort_changed, "serial")
        button_container.append(self.sort_serial_btn)

        self.sort_serial_btn.set_group(self.sort_datetime_btn)

        sort_box.append(button_container)

        return sort_box

    def _create_filter_section(self):
        """Create the Filter section with account type, keyword, and date range"""
        filter_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        filter_label = Gtk.Label(label="Filter")
        filter_label.set_halign(Gtk.Align.START)
        filter_label.add_css_class("heading")
        filter_box.append(filter_label)

        filter_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        filter_container.set_margin_top(8)
        filter_container.set_margin_bottom(8)
        filter_container.set_margin_start(8)
        filter_container.set_margin_end(8)
        filter_container.add_css_class("card")

        account_type_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        account_type_box.set_hexpand(True)
        account_type_box.set_margin_start(8)
        account_type_label = Gtk.Label(label="Account type")
        account_type_label.set_halign(Gtk.Align.START)
        account_type_label.add_css_class("caption")
        account_type_label.set_margin_top(4)
        account_type_box.set_margin_bottom(4)
        account_type_box.append(account_type_label)

        account_types = Gtk.StringList()
        account_types.append("All types")
        account_types.append("Asset")
        account_types.append("Liability")
        account_types.append("Income")
        account_types.append("Expense")

        self.account_type_dropdown = Gtk.DropDown(model=account_types)
        self.account_type_dropdown.set_selected(0)
        self.account_type_dropdown.connect("notify::selected", self.on_filter_changed)
        account_type_box.append(self.account_type_dropdown)

        filter_container.append(account_type_box)

        keyword_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        keyword_box.set_hexpand(True)

        keyword_label = Gtk.Label(label="Keyword or Account path")
        keyword_label.set_halign(Gtk.Align.START)
        keyword_label.add_css_class("caption")
        keyword_label.set_margin_top(4)
        keyword_box.set_margin_bottom(4)
        keyword_box.append(keyword_label)

        self.keyword_entry = Gtk.Entry()
        self.keyword_entry.set_placeholder_text("Search in description or path...")
        self.keyword_entry.set_text("")
        self.keyword_entry.connect("changed", self.on_filter_changed)
        keyword_label.set_margin_top(4)
        keyword_box.append(self.keyword_entry)

        filter_container.append(keyword_box)

        date_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        date_box.set_hexpand(True)

        date_label = Gtk.Label(label="Date range")
        date_label.set_halign(Gtk.Align.START)
        date_label.add_css_class("caption")
        date_label.set_margin_top(4)
        date_box.set_margin_bottom(4)
        date_box.append(date_label)

        date_range_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        today = date.today()
        try:
            one_month_ago = today.replace(month=today.month - 1)
        except ValueError:
            one_month_ago = today.replace(year=today.year - 1, month=12)

        self.date_start_entry = Gtk.Entry()
        self.date_start_entry.set_placeholder_text("MM-DD")
        self.date_start_entry.set_text(one_month_ago.strftime("%m-%d"))
        self.date_start_entry.set_max_width_chars(10)
        self.date_start_entry.connect("changed", self.on_filter_changed)
        date_range_box.append(self.date_start_entry)

        to_label = Gtk.Label(label="to")
        to_label.add_css_class("dim-label")
        date_range_box.append(to_label)

        self.date_end_entry = Gtk.Entry()
        self.date_end_entry.set_placeholder_text("MM-DD")
        self.date_end_entry.set_text(today.strftime("%m-%d"))
        self.date_end_entry.set_max_width_chars(10)
        self.date_end_entry.connect("changed", self.on_filter_changed)
        date_range_box.append(self.date_end_entry)

        calendar_btn = Gtk.Button()
        calendar_btn.set_icon_name("x-office-calendar-symbolic")
        calendar_btn.add_css_class("flat")
        calendar_btn.connect("clicked", self.on_calendar_clicked)
        date_range_box.append(calendar_btn)

        date_box.append(date_range_box)

        filter_container.append(date_box)

        filter_box.append(filter_container)

        return filter_box

    def on_filter_changed(self, widget, *args):
        """Handle filter changes - track which filter was last updated"""
        if widget == self.account_type_dropdown:
            self.active_filter = "account_type"
        elif widget == self.keyword_entry:
            self.active_filter = "keyword"
        elif widget in (self.date_start_entry, self.date_end_entry):
            self.active_filter = "date"

        self.refresh_data()

    def on_calendar_clicked(self, button):
        today = date.today()
        try:
            one_month_ago = today.replace(month=today.month - 1)
        except ValueError:
            one_month_ago = today.replace(year=today.year - 1, month=12)

        self._start_date = one_month_ago.strftime("%Y-%m-%d")
        self._end_date = today.strftime("%Y-%m-%d")

        dialog = Gtk.Dialog(transient_for=self.get_root(), modal=True)
        dialog.set_title("Select Date Range")
        dialog.set_default_size(400, 450)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Apply", Gtk.ResponseType.OK)
        content = dialog.get_content_area()
        content.set_spacing(16)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.append(main_box)
        instruction = Gtk.Label(
            label="Click once for start date, click again for end date"
        )
        instruction.add_css_class("dim-label")
        instruction.set_wrap(True)
        instruction.set_halign(Gtk.Align.START)
        main_box.append(instruction)
        self._calendar = Gtk.Calendar()
        self._calendar.set_margin_start(12)
        self._calendar.set_margin_end(12)
        self._calendar.set_margin_top(8)
        self._calendar.set_margin_bottom(8)
        main_box.append(self._calendar)
        selection_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        selection_box.set_halign(Gtk.Align.CENTER)
        main_box.append(selection_box)
        self._start_label = Gtk.Label()
        self._start_label.set_markup("<b>Start:</b> {}".format(self._start_date))
        selection_box.append(self._start_label)
        selection_box.append(Gtk.Label(label="→"))
        self._end_label = Gtk.Label()
        self._end_label.set_markup("<b>End:</b> {}".format(self._end_date))
        selection_box.append(self._end_label)

        # Mark default dates on calendar
        self._calendar.select_day(
            GLib.DateTime.new_local(today.year, today.month, today.day, 0, 0, 0)
        )
        self._calendar.mark_day(one_month_ago.day)
        self._calendar.mark_day(today.day)

        self._calendar.connect("day-selected", self._on_calendar_day_selected)
        dialog.connect("response", self._on_calendar_response)
        dialog.present()

    def _on_calendar_day_selected(self, cal):
        date = cal.get_date()
        date_str = "{}-{:02d}-{:02d}".format(
            date.get_year(), date.get_month(), date.get_day_of_month()
        )
        if self._start_date is None or self._end_date is not None:
            self._start_date = date_str
            self._end_date = None
            self._start_label.set_markup("<b>Start:</b> {}".format(date_str))
            self._end_label.set_markup("<b>End:</b> --")
            self._calendar.mark_day(date.get_day_of_month())
        else:
            self._end_date = date_str
            self._end_label.set_markup("<b>End:</b> {}".format(date_str))
            self._calendar.mark_day(date.get_day_of_month())

    def _on_calendar_response(self, dialog, response):
        if response == Gtk.ResponseType.OK and self._start_date and self._end_date:
            start = datetime.strptime(self._start_date, "%Y-%m-%d").date()
            end = datetime.strptime(self._end_date, "%Y-%m-%d").date()
            filtered = [
                e
                for e in self.entries
                if e.tx_date and start <= e.tx_date.date() <= end
            ]
            self._reload_store(filtered)
        self._calendar.unmark_day(self._calendar.get_date().get_day_of_month())
        dialog.destroy()

    def on_sort_changed(self, button, sort_type):
        """Handle sort option changes"""
        if button.get_active():
            logg.info(f"Sort changed to: {sort_type}")
            self._sort_and_reload(sort_type)

    def on_fab_clicked(self, button):
        logg.info("FAB clicked - opening create entry window")

        create_page = create_entry_page(self.nav_view, self.entry_controller)
        self.nav_view.push(create_page)

    def refresh_data(self):
        filtered = list(self.entries)

        if self.active_filter == "account_type":
            account_type_idx = self.account_type_dropdown.get_selected()
            account_type = self.account_type_dropdown.get_model().get_string(
                account_type_idx
            )
            if account_type != "All types":
                filtered = [
                    e
                    for e in filtered
                    if e.source_type.lower() == account_type.lower()
                    or e.dest_type.lower() == account_type.lower()
                ]

        elif self.active_filter == "keyword":
            keyword = self.keyword_entry.get_text().strip().lower()
            if keyword:
                filtered = [
                    e
                    for e in filtered
                    if keyword in (e.description or "").lower()
                    or keyword in (e.source_path or "").lower()
                    or keyword in (e.dest_path or "").lower()
                ]

        elif self.active_filter == "date":
            date_start = self.date_start_entry.get_text().strip()
            date_end = self.date_end_entry.get_text().strip()
            logg.info("Date range selected: {} to {}".format(date_start, date_end))
            if date_start:
                filtered = [e for e in filtered if str(e.tx_date)[5:10] >= date_start]
            if date_end:
                filtered = [e for e in filtered if str(e.tx_date)[5:10] <= date_end]

        sort_type = "serial" if self.sort_serial_btn.get_active() else "datetime"
        if sort_type == "serial":
            filtered = sorted(filtered, key=lambda e: e.serial)
        else:
            filtered = sorted(
                filtered, key=lambda e: (e.tx_date, e.serial), reverse=True
            )

        self._reload_store(filtered)

    def on_create_window_closed(self, window):
        logg.info("Create entry window closed")
        if self.refresh_callback:
            self.refresh_callback()
        return False

    def _create_table_section(self):
        """Create the entry list table with all columns"""
        table_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self.entry_store = Gio.ListStore.new(EntryItem)
        selection_model = Gtk.SingleSelection.new(self.entry_store)

        column_view = Gtk.ColumnView(model=selection_model)
        column_view.add_css_class("data-table")
        column_view.set_show_row_separators(True)
        column_view.set_show_column_separators(True)

        serial_factory = Gtk.SignalListItemFactory()
        serial_factory.connect("setup", self._on_serial_setup)
        serial_factory.connect("bind", self._on_serial_bind)
        serial_col = Gtk.ColumnViewColumn(title="Serial No", factory=serial_factory)
        serial_col.set_fixed_width(70)
        column_view.append_column(serial_col)

        date_factory = Gtk.SignalListItemFactory()
        date_factory.connect("setup", self._on_date_setup)
        date_factory.connect("bind", self._on_date_bind)
        date_col = Gtk.ColumnViewColumn(title="Transaction date", factory=date_factory)
        date_col.set_fixed_width(100)
        column_view.append_column(date_col)

        desc_factory = Gtk.SignalListItemFactory()
        desc_factory.connect("setup", self._on_desc_setup)
        desc_factory.connect("bind", self._on_desc_bind)
        desc_col = Gtk.ColumnViewColumn(title="Description", factory=desc_factory)
        desc_col.set_expand(True)
        column_view.append_column(desc_col)

        auth_factory = Gtk.SignalListItemFactory()
        auth_factory.connect("setup", self._on_auth_setup)
        auth_factory.connect("bind", self._on_auth_bind)
        auth_col = Gtk.ColumnViewColumn(title="Auth state", factory=auth_factory)
        auth_col.set_fixed_width(120)
        column_view.append_column(auth_col)

        source_factory = Gtk.SignalListItemFactory()
        source_factory.connect("setup", self._on_source_setup)
        source_factory.connect("bind", self._on_source_bind)
        source_col = Gtk.ColumnViewColumn(title="Source", factory=source_factory)
        source_col.set_expand(True)
        column_view.append_column(source_col)

        dest_factory = Gtk.SignalListItemFactory()
        dest_factory.connect("setup", self._on_dest_setup)
        dest_factory.connect("bind", self._on_dest_bind)
        dest_col = Gtk.ColumnViewColumn(title="Destination", factory=dest_factory)
        dest_col.set_expand(True)
        column_view.append_column(dest_col)

        action_factory = Gtk.SignalListItemFactory()
        action_factory.connect("setup", self._on_action_setup)
        action_factory.connect("bind", self._on_action_bind)
        action_col = Gtk.ColumnViewColumn(title="Action", factory=action_factory)
        action_col.set_fixed_width(80)
        column_view.append_column(action_col)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(column_view)

        table_box.append(scrolled)

        return table_box

    def _on_serial_setup(self, factory, list_item):
        label = Gtk.Label()
        label.set_halign(Gtk.Align.START)
        label.add_css_class("monospace")
        list_item.set_child(label)

    def _on_serial_bind(self, factory, list_item):
        entry = list_item.get_item()
        label = list_item.get_child()
        label.set_text(str(entry.serial))

    def _on_date_setup(self, factory, list_item):
        label = Gtk.Label()
        label.set_halign(Gtk.Align.START)
        label.add_css_class("monospace")
        list_item.set_child(label)

    def _on_date_bind(self, factory, list_item):
        entry = list_item.get_item()
        label = list_item.get_child()
        date_only = str(entry.tx_date)[:10]
        label.set_label(date_only)

    def _on_desc_setup(self, factory, list_item):
        label = Gtk.Label()
        label.set_halign(Gtk.Align.START)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        list_item.set_child(label)

    def _on_desc_bind(self, factory, list_item):
        entry = list_item.get_item()
        label = list_item.get_child()
        label.set_text(entry.description)

    def _on_auth_setup(self, factory, list_item):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.set_halign(Gtk.Align.CENTER)

        badge = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        badge.set_margin_top(4)
        badge.set_margin_bottom(4)
        badge.set_margin_start(8)
        badge.set_margin_end(8)
        badge.add_css_class("badge")

        icon = Gtk.Label()
        badge.append(icon)

        text = Gtk.Label()
        text.add_css_class("caption")
        badge.append(text)

        box.append(badge)
        list_item.set_child(box)

    def _on_auth_bind(self, factory, list_item):
        """Bind auth state data with styling"""
        entry = list_item.get_item()
        box = list_item.get_child()
        badge = box.get_first_child()

        badge.remove_css_class("auth-trusted")
        badge.remove_css_class("auth-not-trusted")
        badge.remove_css_class("auth-unknown")
        badge.remove_css_class("auth-invalid")
        badge.remove_css_class("auth-unsigned")

        icon_label = badge.get_first_child()
        text_label = icon_label.get_next_sibling()

        auth_state = entry.auth_state
        if auth_state == "trusted":
            badge.add_css_class("auth-trusted")
            icon_label.set_text("✓")
            text_label.set_text("Trusted")
        elif auth_state == "not_trusted":
            badge.add_css_class("auth-not-trusted")
            icon_label.set_text("⚠")
            text_label.set_text("Not Trusted")
        elif auth_state == "unknown":
            badge.add_css_class("auth-unknown")
            icon_label.set_text("?")
            text_label.set_text("Unknown Key")
        elif auth_state == "invalid":
            badge.add_css_class("auth-invalid")
            icon_label.set_text("✗")
            text_label.set_text("Invalid")
        else:
            badge.add_css_class("auth-unsigned")
            icon_label.set_text("○")
            text_label.set_text("No Key")

    def _on_source_setup(self, factory, list_item):
        """Setup source cell (compressed format)"""
        label = Gtk.Label()
        label.set_halign(Gtk.Align.START)
        label.add_css_class("monospace")
        label.add_css_class("source-cell")
        label.set_margin_start(8)
        list_item.set_child(label)

    def _on_source_bind(self, factory, list_item):
        """Bind source data in compressed format: [BTC] Expense.deposit/rent"""
        entry = list_item.get_item()
        label = list_item.get_child()

        # Format: [UNIT] Type.path
        formatted = f"[{entry.source_unit}]\n{entry.source_type}.{entry.source_path}"
        label.set_text(formatted)

    def _on_dest_setup(self, factory, list_item):
        """Setup destination cell (compressed format)"""
        label = Gtk.Label()
        label.set_halign(Gtk.Align.START)
        label.add_css_class("monospace")
        label.add_css_class("dest-cell")
        label.set_margin_start(8)
        list_item.set_child(label)

    def _on_dest_bind(self, factory, list_item):
        """Bind destination data in compressed format"""
        entry = list_item.get_item()
        label = list_item.get_child()

        # Format: [UNIT] Type.path
        formatted = f"[{entry.dest_unit}]\n{entry.dest_type}.{entry.dest_path}"
        label.set_text(formatted)

    def _on_action_setup(self, factory, list_item):
        """Setup action cell"""
        button = Gtk.Button(label="View")
        button.add_css_class("link")
        button.add_css_class("accent")
        button.set_halign(Gtk.Align.CENTER)
        button.handler_id = None
        list_item.set_child(button)

    def _on_action_bind(self, factory, list_item):
        """Bind action button"""
        entry = list_item.get_item()
        button = list_item.get_child()

        if hasattr(button, "handler_id") and button.handler_id is not None:
            button.disconnect(button.handler_id)

        button.handler_id = button.connect("clicked", self._on_view_entry, entry)

    def _on_view_entry(self, button, entry):
        """Handle view button click"""
        logg.info(f"View entry clicked: {entry.serial}")
        details_page = create_entry_details_page(
            entry,
            self.nav_view,
            self.entry_controller,
            self.toast_overlay,
            self.entry_controller.get_asset_bytes,
        )
        self.nav_view.push(details_page)

    def format_attachments(self, assets):
        if not assets:
            return ""

        return ", ".join(
            a.slug or a.uuid or (a.digest.hex()[:8] if a.digest else "unknown")
            for a in assets
        )

    def _make_entry_item(self, entry) -> EntryItem:
        signers_raw = entry.signer_pubkeys
        signers_display = ", ".join([f"{k[:8]}...{k[-6:]}" for k in signers_raw])
        return EntryItem(
            serial=entry.serial,
            parent_digest=entry.parent_digest,
            tx_date=entry.tx_date,
            tx_ref=entry.tx_reference,
            tx_date_rg=entry.date_registered,
            description=entry.description,
            auth_state="trusted",
            amount=entry.amount,
            source_path=entry.source_path,
            source_type=entry.source_type,
            source_unit=entry.source_unit,
            unit_index=entry.unit_index,
            signers=signers_display,
            signers_raw=signers_raw,
            dest_path=entry.dest_path,
            dest_unit=entry.dest_unit,
            dest_type=entry.dest_type,
            attachments=self.format_attachments(entry.attachments),
            attachments_raw=entry.attachments,
        )

    def _reload_store(self, entries):
        self.entry_store.remove_all()
        for entry in entries:
            self.entry_store.append(self._make_entry_item(entry))

    def _load_entries(self):
        self.entries = self.entry_controller.get_all_entries()
        self._sort_and_reload("datetime")

    def _sort_and_reload(self, sort_type):
        if sort_type == "serial":
            sorted_entries = sorted(self.entries, key=lambda e: e.serial)
        elif sort_type == "datetime":
            sorted_entries = sorted(
                self.entries, key=lambda e: (e.tx_date, e.serial), reverse=True
            )
        self._reload_store(sorted_entries)
