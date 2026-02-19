import base64
import logging
from usawa.crypto import ACL
from usawa.service import UnixClient
from usawa.core.entry_service import EntryService
from usawa.ledger import Ledger
from usawa.storage.ledger_repository import LedgerRepository
from usawa.store import LedgerStore
from gi.repository import Adw, Gtk
from whee.valkey import ValkeyStore

from usawa.gui.controllers.entry_controller import EntryController
from usawa.gui.models.entry_item import EntryItem
from usawa.gui.views.entry_list_view import EntryListView
from usawa import Ledger, DemoWallet, load

logg = logging.getLogger("gui.mainwindow")

class UsawaMainWindow(Gtk.ApplicationWindow):


    def __init__(self, application,ledger_path=None, **kwargs):
        super().__init__(application=application, **kwargs)
        
        self.set_title("Usawa")
        self.set_default_size(1000, 600)
        
        # Main box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(main_box)

        ledger_tree = load(ledger_path)
        ledger = Ledger.from_tree(ledger_tree)
        

        db = ValkeyStore('')
        self.client = UnixClient(path="")
       
        store = LedgerStore(db, ledger)
        pk = store.get_key()
        wallet = DemoWallet(privatekey=pk)
        logg.debug("wallet pk: %s pubk: %s", wallet.privkey().hex(), wallet.pubkey().hex())
        ledger.set_wallet(wallet)


        ledger.acl = ACL.from_wallet(wallet)
        store.load(acl=ledger.acl)

        logg.debug("Ledger has %d entries", len(ledger.entries))

        for serial, entry in ledger.entries.items():
            logg.debug("Entry serial: %s", serial)

     
        repository = LedgerRepository(ledger_store=store,unix_client=self.client,wallet=wallet)

        entry_service = EntryService(repository=repository,unixClient= self.client)
        self.entry_controller = EntryController(entry_service=entry_service)

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
        
        entry_list_view = EntryListView(nav_view=self.nav_view,entry_controller=self.entry_controller)
        page.set_child(entry_list_view)
        
        return page

