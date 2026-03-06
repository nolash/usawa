import logging
from gi.repository import Gtk, Adw,Gio,Pango
from pathlib import Path
import mimetypes

logg = logging.getLogger("gui.create_entry_view")


def create_entry_page(nav_view, controller):
    """Create a new entry page"""
    page = Adw.NavigationPage(
        title="Create New Entry",
        tag="create-entry"
    )

    view = CreateEntryView(nav_view, controller)
    page.set_child(view)
    
    return page


class CreateEntryView(Gtk.Box):
    """Create entry view - UI ONLY"""
    
    def __init__(self, nav_view, controller):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        
        self.nav_view = nav_view
        self.controller = controller
        self.attachment_paths: list[str] = []
        
        self._build_ui(nav_view)
    
    def _build_ui(self,nav_view):
        """Build the UI"""
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
        
        attachments_section = self._create_attachments_section()
        content.append(attachments_section)
        
        warning = self._create_warning()
        content.append(warning)
        
        scrolled.set_child(content)
        self.append(scrolled)
        
        action_bar = self._create_action_bar()
        self.append(action_bar)


    def _create_header(self,nav_view):
        """Create the header with back button and serial number"""
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
        
        serial_badge = Gtk.Label(label=f"Next Serial: #{self.controller.next_serial():04d}")
        serial_badge.add_css_class("caption")
        serial_badge.add_css_class("accent")
        serial_badge.set_margin_start(8)
        serial_badge.set_margin_end(8)
        serial_badge.set_margin_top(4)
        serial_badge.set_margin_bottom(4)
        header_box.append(serial_badge)
        return header_box
    
    def _create_basic_section(self):
        """Create basic details section - UI ONLY"""
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
        
        amount_label = Gtk.Label(label="Amount")
        amount_label.set_halign(Gtk.Align.START)
        amount_label.add_css_class("dim-label")
        section_box.append(amount_label)
        
        self.amount_entry = Gtk.Entry()
        self.amount_entry.set_placeholder_text("0.00")
        section_box.append(self.amount_entry)
        
        ledger_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        ledger_box.set_homogeneous(True)
        

        source_card = self._create_ledger_side_card("Source", is_source=True)
        ledger_box.append(source_card)
        
    
        dest_card = self._create_ledger_side_card("Destination", is_source=False)
        ledger_box.append(dest_card)
        
        section_box.append(ledger_box)
        
        return section_box
    

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
    


    def _create_ledger_side_card( self,title, is_source=True):
        """Create a card for source or destination with its own unit"""
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
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
        
    
        fields = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        fields.set_margin_start(8)
        fields.set_margin_end(8)
        fields.set_margin_bottom(8)
              
        unit_label = Gtk.Label(label="Unit")
        unit_label.set_halign(Gtk.Align.START)
        unit_label.add_css_class("caption")
        fields.append(unit_label)
        
        units = Gtk.StringList()
        units.append("Bitcoin(BTC)")
       
        
        unit_dropdown = Gtk.DropDown(model=units)
        unit_dropdown.set_selected(0)  
        fields.append(unit_dropdown)
        
        type_label = Gtk.Label(label="Account type")
        type_label.set_halign(Gtk.Align.START)
        type_label.add_css_class("caption")
        fields.append(type_label)
        
        types = Gtk.StringList()
        if is_source:
            types.append("Expense")
            types.append("Asset")
            types.append("Liability")
            types.append("Income")
        else:
            types.append("Asset")
            types.append("Expense")
            types.append("Liability")
            types.append("Income")
        
        type_dropdown = Gtk.DropDown(model=types)
        fields.append(type_dropdown)
        
        
        path_label = Gtk.Label(label="Account path")
        path_label.set_halign(Gtk.Align.START)
        path_label.add_css_class("caption")
        fields.append(path_label)
        
        path_entry = Gtk.Entry()
        path_entry.set_text("general")
        fields.append(path_entry)
        
        card.append(fields)
        
        
        if is_source:
            self.source_unit_dropdown = unit_dropdown
            self.source_type_dropdown = type_dropdown
            self.source_path_entry = path_entry
        else:
            self.dest_unit_dropdown = unit_dropdown
            self.dest_type_dropdown = type_dropdown
            self.dest_path_entry = path_entry
        
        return card
    

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
        text.set_markup("<b>Note:</b> Entries cannot be saved as drafts. You must either Finalize or Discard.")
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
            parent=self.get_root(),
            callback=self._on_files_selected
        )

    def _on_files_selected(self, dialog, result):
        """Handle multiple file selection"""
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
        icon_name = "text-x-generic-symbolic"  # Default
        
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
            filename=filename,
            file_path=file_path,
            metadata=f"{mime_type} • {size_str}"
        )

        self.attachment_list.append(attachment_row)
        logg.info(f"Added attachment: {filename} ({size_str})")

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable form"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def _on_finalize(self, button):
        """Handle finalize button - delegates to controller"""
        entry = self.controller.collect_entry_data(self)
        if self.attachment_paths:
           entry.attachments.extend(self.attachment_paths)
        
        if entry is None:
            self._show_error_dialog("Invalid Input", "Please check your entries and try again.")
            return
        
        success = self.controller.finalize_entry(entry)
        if success:
            self.controller.notify_entry_created()
            self.nav_view.pop() 
        else:
            self._show_error_dialog("Save Failed", 
                                   "Could not save the entry. Please try again.")
    
    def _show_error_dialog(self, title, message):
        """Show error dialog"""
        dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading=title,
            body=message
        )
        dialog.add_response("ok", "OK")
        dialog.present()