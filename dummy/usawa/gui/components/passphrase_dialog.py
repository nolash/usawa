import logging
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, GLib

logg = logging.getLogger("gui.passphrase_dialog")


class PassphraseDialog(Adw.Dialog):
    """Dialog that prompts the user for a wallet passphrase, decrypts the key,
    and calls a success or failure callback.

    :param store: LedgerStore instance to retrieve the key from.
    :type store: usawa.LedgerStore
    :param wallet_class: Wallet class to instantiate from the stored key.
    :type wallet_class: type
    :param on_success: Callback called with the unlocked wallet on success.
    :type on_success: callable(wallet)
    :param on_cancel: Optional callback called if the dialog is dismissed without unlocking.
    :type on_cancel: callable or None
    """

    def __init__(self, store, wallet_class, on_success, on_cancel=None):
        super().__init__()
        self.store = store
        self.wallet_class = wallet_class
        self.on_success = on_success
        self.on_cancel = on_cancel
        self._unlocked = False

        self.set_title("Unlock Wallet")
        self.set_content_width(360)
        self.set_can_close(True)

        self._build_ui()
        self.connect("closed", self._on_closed)

    def _build_ui(self):
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)

        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        toolbar_view.add_top_bar(header)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(24)
        content.set_margin_end(24)
        toolbar_view.set_content(content)

        icon_label = Gtk.Image.new_from_icon_name("channel-secure-symbolic")
        icon_label.set_css_classes(["title-1"])
        content.append(icon_label)

        title = Gtk.Label(label="Wallet Locked")
        title.set_css_classes(["title-2"])
        content.append(title)

        subtitle = Gtk.Label(label="Enter your passphrase to unlock the wallet.")
        subtitle.set_wrap(True)
        subtitle.set_justify(Gtk.Justification.CENTER)
        subtitle.set_css_classes(["dim-label"])
        content.append(subtitle)

        self.passphrase_row = Adw.PasswordEntryRow()
        self.passphrase_row.set_title("Passphrase")
        self.passphrase_row.connect("entry-activated", self._on_unlock_clicked)

        group = Adw.PreferencesGroup()
        group.add(self.passphrase_row)
        content.append(group)

        self.error_label = Gtk.Label(label="")
        self.error_label.set_css_classes(["error"])
        self.error_label.set_visible(False)
        self.error_label.set_wrap(True)
        self.error_label.set_justify(Gtk.Justification.CENTER)
        content.append(self.error_label)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(150)
        content.append(self.stack)

        self.unlock_button = Gtk.Button(label="Unlock")
        self.unlock_button.set_css_classes(["pill", "suggested-action"])
        self.unlock_button.set_halign(Gtk.Align.CENTER)
        self.unlock_button.connect("clicked", self._on_unlock_clicked)
        self.stack.add_named(self.unlock_button, "button")

        # Spinner
        spinner_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        spinner_box.set_halign(Gtk.Align.CENTER)
        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(20, 20)
        spinner_label = Gtk.Label(label="Unlocking…")
        spinner_label.set_css_classes(["dim-label"])
        spinner_box.append(self.spinner)
        spinner_box.append(spinner_label)
        self.stack.add_named(spinner_box, "spinner")

        self.stack.set_visible_child_name("button")

    def _on_unlock_clicked(self, *_):
        passphrase = self.passphrase_row.get_text().strip()
        if not passphrase:
            self._show_error("Please enter your passphrase.")
            return

        self._set_loading(True)
        threading.Thread(
            target=self._do_unlock, args=(passphrase,), daemon=True
        ).start()

    def _do_unlock(self, passphrase):
        try:
            wallet = self.store.get_key(
                wallet_class=self.wallet_class,
                passphrase=passphrase,
            )
            GLib.idle_add(self._unlock_success, wallet)
        except Exception as e:
            logg.warning("Passphrase unlock failed: %s", e)
            GLib.idle_add(self._unlock_failure, str(e))

    def _unlock_success(self, wallet):
        logg.info("Wallet unlocked successfully")
        self._set_loading(False)
        self._unlocked = True
        self.force_close()
        if self.on_success:
            self.on_success(wallet)

    def _unlock_failure(self, error_msg):
        self._set_loading(False)
        self._show_error("Wrong passphrase. Please try again.")
        self._shake_entry()

    def _set_loading(self, loading: bool):
        self.passphrase_row.set_sensitive(not loading)
        if loading:
            self.spinner.start()
            self.stack.set_visible_child_name("spinner")
        else:
            self.spinner.stop()
            self.stack.set_visible_child_name("button")

    def _show_error(self, message: str):
        self.error_label.set_label(message)
        self.error_label.set_visible(True)

    def _shake_entry(self):
        """Apply shake CSS animation to the passphrase entry row."""
        self.passphrase_row.add_css_class("shake")

        def remove_shake():
            self.passphrase_row.remove_css_class("shake")
            return False

        GLib.timeout_add(400, remove_shake)

    def _on_closed(self, *_):
        if not self._unlocked and self.on_cancel:
            self.on_cancel()


# CSS for the shake animation
PASSPHRASE_DIALOG_CSS = """
@keyframes shake {
  0%   { margin-left: 0; }
  20%  { margin-left: -8px; }
  40%  { margin-left: 8px; }
  60%  { margin-left: -6px; }
  80%  { margin-left: 6px; }
  100% { margin-left: 0; }
}

.shake {
  animation: shake 0.4s ease;
}
"""
