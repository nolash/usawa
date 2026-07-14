import logging
from usawa.crypto import DemoWallet
from usawa.gui.components.passphrase_dialog import (
    PASSPHRASE_DIALOG_CSS,
    PassphraseDialog,
)
from .core.entry_service import EntryService
from usawa.storage.ledger_repository import LedgerRepository
from gi.repository import Adw, Gtk, Gio, GLib, Gdk
from usawa.gui.controllers.entry_controller import EntryController
from usawa.gui.views.entry_list_view import EntryListView
from datetime import datetime
import usawa.error

logg = logging.getLogger("gui.mainwindow")


class UsawaMainWindow(Adw.ApplicationWindow):

    def __init__(self, application, ctx, **kwargs):
        super().__init__(application=application, **kwargs)

        self.set_title("Usawa")
        self.set_default_size(1000, 600)

        toolbar_view = Adw.ToolbarView()
        self.set_content(toolbar_view)

        header = Adw.HeaderBar()

        menu_button = self._create_menu_button()
        header.pack_end(menu_button)

        toolbar_view.add_top_bar(header)

        self.toast_overlay = Adw.ToastOverlay()
        toolbar_view.set_content(self.toast_overlay)

        self.ctx = ctx

        self.nav_view = Adw.NavigationView()
        self.toast_overlay.set_child(self.nav_view)

        self._setup_actions()
        GLib.idle_add(self._check_wallet_status)

    def _create_menu_button(self):
        menu = Gio.Menu()
        menu.append("Export Ledger", "app.export-ledger")

        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.set_menu_model(menu)
        menu_button.set_tooltip_text("Main menu")

        return menu_button

    def _setup_actions(self):
        export_action = Gio.SimpleAction.new("export-ledger", None)
        export_action.connect("activate", lambda a, p: self._on_export_clicked())
        self.get_application().add_action(export_action)

    def _on_export_clicked(self):
        file_dialog = Gtk.FileDialog()
        file_dialog.set_title("Export Ledger to XML")
        default_name = f"ledger_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
        file_dialog.set_initial_name(default_name)

        filters = Gio.ListStore.new(Gtk.FileFilter)

        xml_filter = Gtk.FileFilter()
        xml_filter.set_name("XML Files")
        xml_filter.add_pattern("*.xml")
        filters.append(xml_filter)

        file_dialog.set_filters(filters)
        file_dialog.set_default_filter(xml_filter)

        file_dialog.save(parent=self, callback=self._on_export_file_selected)

    def _on_export_file_selected(self, dialog, result):
        try:
            file = dialog.save_finish(result)
            if file:
                file_path = file.get_path()
                success, error_msg = self.entry_controller.export_ledger(file_path)

                if success:
                    self._show_success_toast(f"Exported to {file_path}")
                else:
                    self._show_error_dialog("Export Failed", error_msg)
        except Exception as e:
            logg.debug(f"Export cancelled: {e}")

    def _show_success_toast(self, message):
        toast = Adw.Toast.new(message)
        toast.set_timeout(3)
        self.toast_overlay.add_toast(toast)

    def _create_entry_list_page(self):
        page = Adw.NavigationPage(title="Ledger Entries", tag="entry-list")
        entries = []
        self.entry_list_view = EntryListView(
            ctx=self.ctx,
            nav_view=self.nav_view,
            entry_controller=self.entry_controller,
            entries=entries,
            refresh_callback=self.refresh_entries,
            toast_overlay=self.toast_overlay,
        )
        self.entry_list_view._load_entries()
        page.set_child(self.entry_list_view)

        return page

    def refresh_entries(self):
        logg.info("MainWindow refreshing entries")
        self.entry_list_view._load_entries()

    def _check_wallet_status(self):
        try:
            self.ctx.load_wallet(replace=True, signing=True)
            self._init_with_wallet()
        except usawa.error.VerifyError:
            dialog = PassphraseDialog(
                # store=self.ctx.keystore,
                ctx=self.ctx,
                wallet_class=DemoWallet,
                on_success=self._init_with_wallet,
                on_cancel=self._on_wallet_cancelled,
            )
            dialog.present(self)

    def _init_with_wallet(self):
        repository = LedgerRepository(self.ctx)
        entry_service = EntryService(repository=repository)
        self.entry_controller = EntryController(
            ctx=self.ctx, entry_service=entry_service
        )
        self.entry_controller.add_entry_created_listener(self.refresh_entries)

        entry_list_page = self._create_entry_list_page()
        self.nav_view.add(entry_list_page)

    def _on_wallet_cancelled(self):
        self.get_application().quit()

    def _load_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_string(PASSPHRASE_DIALOG_CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )
