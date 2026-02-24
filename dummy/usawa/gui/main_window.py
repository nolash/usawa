import logging
from usawa.service import UnixClient
from usawa.core.entry_service import EntryService
from usawa.storage.ledger_repository import LedgerRepository
from gi.repository import Adw, Gtk

from usawa.gui.controllers.entry_controller import EntryController
from usawa.gui.views.entry_list_view import EntryListView

logg = logging.getLogger("gui.mainwindow")

class UsawaMainWindow(Gtk.ApplicationWindow):


    def __init__(self, application,ledger_path=None, **kwargs):
        super().__init__(application=application, **kwargs)
        
        self.set_title("Usawa")
        self.set_default_size(1000, 600)
        
        # Main box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(main_box)

        self.client = UnixClient(path="")
        repository = LedgerRepository(ledger_path=ledger_path,unix_client=self.client)

        entry_service = EntryService(repository=repository,unixClient= self.client)
        self.entry_controller = EntryController(entry_service=entry_service)
        self.entry_controller.add_entry_created_listener(self.refresh_entries)

        # Navigation view
        self.nav_view = Adw.NavigationView()
        main_box.append(self.nav_view)
        
        entry_list_page = self._create_entry_list_page()
        self.nav_view.add(entry_list_page)


    def _create_entry_list_page(self):
        page = Adw.NavigationPage(
            title="Ledger Entries",
            tag="entry-list"
        )
        entries = []
        self.entry_list_view = EntryListView(nav_view=self.nav_view,entry_controller=self.entry_controller,entries=entries,refresh_callback=self.refresh_entries)
        self.entry_list_view._load_entries()
        page.set_child(self.entry_list_view)
        
        return page

    def refresh_entries(self):
        logg.info("MainWindow refreshing entries")
        self.entry_list_view._load_entries()
