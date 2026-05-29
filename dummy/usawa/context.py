import logging
import getpass

from whee.valkey import ValkeyStore
from whee.fs import FsStore
from usawa import DemoWallet, Ledger
from usawa.account import AccountIndex
from usawa.store import LedgerStore, EntryStore, KeyStore, AssetStore
from usawa.resolve.fs import FSResolver

logg = logging.getLogger('usawa.ctx')


# TODO: move this code to a cli module
def pwgetter():
    return getpass.getpass('passphrase: ')


class UsawaContext:

    pwget = pwgetter

    def __init__(self, cfg, signing=True, pwgetter=None, replay=False):
        self.cfg = cfg
        self.db = None
        self.ledger = None
        self.ledger_path_in = None
        self.ledger_path_out = None
        self.uidx = None
        self.wallet = None
        self.resolver = None
        self.store = None
        self.keystore = None
        self.aidx = None
        self.o = {}
        self.askpass = False
        self.signing = signing
        self.replay = replay
        self.pwgetter = pwgetter


    def set(self, k, v):
        self.o[k] = v


    def get(self, k):
        return self.o.get(k)


    def init(self, args=None, store_scope=None):
        #v = None
        if args != None:
            try:
                self.ledger_path_in = args.i
            except AttributeError:
                pass
        if self.ledger_path_in == None:
            self.ledger_path_in = self.cfg.get('MAIN_LEDGER_FILE')
        #v = None
        if args != None:
            try:
                #v = args.o
                self.ledger_path_out = args.o
            except AttributeError:
                pass
        if self.ledger_path_out == None:
            self.ledger_path_out = self.cfg.get('MAIN_LEDGER_FILE')
        if self.ledger_path_out == None:
            self.ledger_path_out = self.ledger_path_in
        if self.ledger_path_in != None:
            self.load_ledger()
        self.create_store(store_scope=store_scope)
        self.create_resolver()
        self.load_accounts()

        try:
            self.askpass = args.p
        except AttributeError:
            pass
        self.load_wallet()

        if self.replay:
            #self.store.load(unitindex=self.uidx)
            self.store.load()
            self.ledger.truncate()
            logg.debug('replayed ledger {}'.format(self.ledger.to_string()))


    def commit(self, ledger=None):
        if ledger == None:
            ledger = self.ledger
        ledger.truncate()
        ledger.sign()
        f = open(self.ledger_path_out, 'w')
        f.write(ledger.to_string())
        f.close()
        logg.info('wrote new ledger state {} to {}'.format(ledger, self.ledger_path_out))


    def getpw(self):
        pw = self.cfg.get('WALLET_KEY_PASSPHRASE')
        if pw == None:
            if self.askpass:
                if self.pwgetter != None:
                    pw = self.pwgetter()
                else:
                    pw = UsawaContext.pwget()
        return pw


    def load_wallet(self):
        if self.wallet != None:
            raise AttributeError('wallet set')
        if not self.signing:
            self.wallet = self.keystore.get_default_key(DemoWallet)
        else:
            ops = int(self.cfg.get('WALLET_OPSLIMIT', 0))
            mem = int(self.cfg.get('WALLET_MEMLIMIT', 0))
            pw = self.getpw()
            self.wallet = self.keystore.get_key(DemoWallet, passphrase=pw, opslimit=ops, memlimit=mem)
        if self.ledger != None:
            self.ledger.set_wallet(self.wallet)


    def load_ledger(self):
        if self.ledger != None:
            raise AttributeError('ledger set')
        self.ledger = Ledger.from_file(self.ledger_path_in)
        if self.replay:
            self.ledger = Ledger(self.ledger.uidx, acl=self.ledger.acl, topic=self.ledger.topic)
        self.uidx = self.ledger.uidx
        if self.wallet != None:
            self.ledger.set_wallet(self.wallet)


    def load_accounts(self):
        if self.uidx == None:
            logg.info('no unit index, skip accounts')
            return
        s = self.cfg.get('ACCOUNTS_FILE')
        if s:
            self.aidx = AccountIndex.from_file(self.uidx, s)
        else:
            self.aidx = AccountIndex(self.uidx)
        if self.cfg.true('ACCOUNTS_STRICT'):
            self.aidx.lock()


    def create_store(self, store_scope=None):
        if store_scope == None:
            store_scope = 'ledger'
        if self.store != None:
            raise AttributeError('store set')
        if store_scope  == 'ledger':
            if self.ledger == None:
                raise AttributeError('ledger required for ledger store scope')
        if self.cfg.get('STORE_TYPE') == 'valkey':
            dbid = self.cfg.get('VALKEY_ID')
            host = self.cfg.get('VALKEY_HOST')
            port = self.cfg.get('VALKEY_PORT')
            self.db = ValkeyStore('', host=host, port=port)
        elif self.cfg.get('STORE_TYPE') == 'fs':
            base = self.cfg.get('FSSTORE_BASE')
            self.db = FsStore(base=base, dbname='usawa')
        if store_scope == 'ledger':
            self.store = LedgerStore(self.db, self.ledger)
            self.keystore = self.store
        elif store_scope == 'asset' or store_scope == 'entry':
            self.keystore = KeyStore(self.db)
            if store_scope == 'asset':
                self.store = AssetStore(self.db)
            else:
                self.store = EntryStore(self.db)


    def create_resolver(self, resolver_type='fs'):
        if resolver_type != 'fs':
            raise NotImplementedError('only fs resolver available')
        resolver_path = self.cfg.get('FS_RESOLVER_STORE_PATH')
        if resolver_path:
            self.resolver = FSResolver(resolver_path)
        else:
            logg.debug('missing resolver')
        logg.info('created {}'.format(self.resolver))
