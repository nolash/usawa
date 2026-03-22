import logging
import signal
import gi

from usawa.runnable.setup_wallet import setup_wallet

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio
from .main_window import UsawaMainWindow
from usawa.config import load_config

logg = logging.getLogger("gui.app")


class Usawa(Adw.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE, *args, **kwargs
        )
        self.win = None
        self.ledger_file = None
        self.cfg = None
        self.account_list = None
        self.connect("activate", self.on_activate)
        signal.signal(signal.SIGINT, self._handle_sigint)

    def on_activate(self, app):
        self.win = UsawaMainWindow(application=app, ledger_path=self.ledger_file, account_list=self.account_list)
        self.win.present()

    def _handle_sigint(self, *_):
        logg.debug("shutdown")
        self.quit()

    def do_command_line(self, cli):
        args = cli.get_arguments()

        config_dir = None
        filtered_args = []
        i = 1
        while i < len(args):
            if args[i] == "-c":
                if i + 1 < len(args):
                    config_dir = args[i + 1]
                    i += 2
                else:
                    logg.error("-c flag requires a directory argument")
                    return 1
            else:
                filtered_args.append(args[i])
                i += 1

        if len(filtered_args) == 0:
            logg.error("missing ledger file argument")
            return 1

        if filtered_args[0] == "setup-wallet":
            wallet_dir = filtered_args[1] if len(filtered_args) > 1 else None
            setup_wallet(wallet_dir=wallet_dir)
            return 0

        self.ledger_file = filtered_args[0]
        self.cfg = load_config(config_dir=config_dir)
        for k in self.cfg.all():
            logg.debug("config {} => {}".format(k, self.cfg.get(k)))
        self.activate()
        return 0
