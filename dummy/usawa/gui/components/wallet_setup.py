import logging
import os
from gi.repository import Gtk, Adw, GLib, Gio
import threading
import logging
import threading

from usawa.core.usawa_wallet import UsawaWallet


logg = logging.getLogger("gui.wallet_setup_view")


class ImportWalletDialog(Adw.Dialog):

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.set_title("Import Wallet")
        self.set_content_width(400)
        self.set_content_height(300)

        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)

        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        toolbar_view.add_top_bar(header)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(24)
        box.set_margin_end(24)
        toolbar_view.set_content(box)

        icon = Gtk.Image.new_from_icon_name("dialog-password-symbolic")
        icon.set_pixel_size(64)
        box.append(icon)

        title = Gtk.Label(label="Import your wallet")
        title.add_css_class("title-2")
        box.append(title)

        subtitle = Gtk.Label(
            label="Select your privatekey.asc file to unlock your wallet"
        )
        subtitle.set_wrap(True)
        subtitle.set_justify(Gtk.Justification.CENTER)
        subtitle.add_css_class("dim-label")
        box.append(subtitle)

        self.file_label = Gtk.Label(label="No file selected")
        self.file_label.add_css_class("dim-label")
        box.append(self.file_label)

        passphrase_row = Adw.PasswordEntryRow()
        passphrase_row.set_title("Passphrase")
        passphrase_row.set_show_apply_button(False)
        box.append(passphrase_row)
        self.passphrase_row = passphrase_row

        self.spinner = Gtk.Spinner()
        box.append(self.spinner)

        button_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        button_row.set_halign(Gtk.Align.CENTER)
        box.append(button_row)

        self.browse_btn = Gtk.Button(label="Select privatekey.asc")
        self.browse_btn.add_css_class("pill")
        self.browse_btn.connect("clicked", self._on_browse_clicked)
        button_row.append(self.browse_btn)

        self.import_btn = Gtk.Button(label="Import")
        self.import_btn.add_css_class("pill")
        self.import_btn.add_css_class("suggested-action")
        self.import_btn.set_sensitive(False)
        self.import_btn.connect("clicked", self._on_import_clicked)
        button_row.append(self.import_btn)

        self.privatekey_path = None

    def _on_browse_clicked(self, btn):
        file_dialog = Gtk.FileDialog()
        file_dialog.set_title("Select privatekey.asc")
        filter_asc = Gtk.FileFilter()
        filter_asc.set_name("ASC files")
        filter_asc.add_pattern("*.asc")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_asc)
        file_dialog.set_filters(filters)
        file_dialog.open(self.parent, None, self._on_file_selected)

    def _on_file_selected(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file is None:
                return
            self.privatekey_path = file.get_path()
            self.file_label.set_text(os.path.basename(self.privatekey_path))
            self.import_btn.set_sensitive(True)
        except GLib.Error as e:
            logg.debug("file dialog error: %s", e)

    def _on_import_clicked(self, btn):
        if not self.privatekey_path:
            return
        self.import_btn.set_sensitive(False)
        self.browse_btn.set_sensitive(False)
        self.spinner.start()

        passphrase = self.passphrase_row.get_text()

        cfg = self.parent.get_application().cfg
        gpg_dir = cfg.get("MAIN_GPG_DIR")

        threading.Thread(
            target=self._run_decrypt,
            args=(self.privatekey_path, gpg_dir, passphrase),
            daemon=True,
        ).start()

    def _run_decrypt(self, privatekey_path, gpg_dir, passphrase):
        logg.info("running decrypt")
        try:
            wallet = UsawaWallet(
                keyfile=privatekey_path, gpgdir=gpg_dir, passphrase=passphrase
            )
            GLib.idle_add(self._on_success, wallet)
        except Exception as e:
            logg.error("wallet decrypt failed: %s", e)
            GLib.idle_add(self._on_error)

    def _on_success(self, wallet):
        self.spinner.stop()
        # Store wallet on main window for access anywhere in the app
        self.parent.wallet = wallet
        logg.debug(
            "wallet ready, key_id: %s",
            wallet.gpg.list_keys()[0]["keyid"] if wallet else None,
        )
        toast = Adw.Toast.new("Wallet imported successfully")
        toast.set_timeout(3)
        self.parent.toast_overlay.add_toast(toast)
        self.close()
        self.parent._init_with_wallet(wallet)

    def _on_error(self):
        self.spinner.stop()
        self.import_btn.set_sensitive(True)
        self.browse_btn.set_sensitive(True)
        toast = Adw.Toast.new("Failed to decrypt wallet — check your GPG setup")
        toast.set_timeout(5)
        self.parent.toast_overlay.add_toast(toast)
