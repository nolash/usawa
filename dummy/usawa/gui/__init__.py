import logging
import signal
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw,Gio
from .main_window import UsawaMainWindow
logg = logging.getLogger("gui.app")

class Usawa(Adw.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(flags= Gio.ApplicationFlags.HANDLES_COMMAND_LINE,*args, **kwargs)
        self.win = None
        self.ledger_file = None
        self.connect('activate', self.on_activate)
        signal.signal(signal.SIGINT, self._handle_sigint)

    
    def on_activate(self, app):
        self.win = UsawaMainWindow(application=app,ledger_path=self.ledger_file)
        self.win.present()


    def _handle_sigint(self,*_):
        logg.debug("shutdown")
        self.quit()

    def do_command_line(self, cli):
        args = cli.get_arguments()

        if len(args) > 1:
           self.ledger_file = args[1]

        self.activate()
        return 0