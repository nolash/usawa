import logging
import getpass
import hashlib
import sys

from whee.valkey import ValkeyStore
from whee.fs import FsStore
from usawa import DemoWallet, Ledger, UnitIndex
from usawa.account import AccountIndex
from usawa.store import LedgerStore, EntryStore, KeyStore, AssetStore
from usawa.store.keyring import KeyringStore
from usawa.resolve.fs import FSResolver
from usawa.user import UsawaUser

logg = logging.getLogger('usawa.ctx')


# TODO: move this code to a cli module
def pwgetter():
    return getpass.getpass('passphrase: ')




# TODO: Move to ledger internal
def parse_topic(v):
    if v == None:
        return None
    topic = None
    if isinstance(v, str):
        if len(v) > 2:
            if v[:2] == '0x':
                v = v[2:]
                v += b'\x00' * 64
                v = v[:64]
                topic = bytes.fromhex(v)
            else:
                h = hashlib.sha512()
                h.update(v.encode('utf-8'))
                topic = h.digest()
    else:
        raise ValueError('invalid topic {}'.format(v))
    return topic


class UsawaContext:

    pwget = pwgetter

    def __init__(self, cfg, signing=True, pwgetter=None, idgetter=None, replay=False):
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
        self.idgetter = idgetter
        self.fo = None
        self.keyring = None


    def set(self, k, v):
        self.o[k] = v


    def get(self, k):
        return self.o.get(k)


    def __fp_open(self):
        if self.fo:
            return self.fo
        if self.ledger_path_out == None:
            return sys.stdout
        self.fo = open(self.ledger_path_out, 'w')
        return self.fo


    def __fp_close(self):
        if self.fo:
            self.fo.close()


    def write(self, v):
        f = self.__fp_open()
        f.write(v)
        self.__fp_close()


    def ledger_from_args(self, args):
        try:
            unitspec = args.unit[0].split(':')
            unit = unitspec[0]
            logg.debug('have unit {}'.format(unit))
            unit_precision = None
            try:
                unit_precision = unitspec[1]
            except IndexError:
                unit_precision = UnitIndex.default_precision
        except IndexError:
            unit = UnitIndex.default_unit 
            unit_precision = UnitIndex.default_precision
        self.uidx = UnitIndex(unit, precision=unit_precision)
        for v in args.unit[1:]:
            unitspec = v.split(':')
            unit = unitspec[0]
            unit_precision = None
            try:
                unit_precision = unitspec[1]
            except IndexError:
                unit_precision = UnitIndex.default_precision
            uidx.add(unit, precision=unit_precision)
        self.topic = parse_topic(self.cfg.get('LEDGER_TOPIC'))
        self.ledger = Ledger(self.uidx, topic=self.topic, src=args.src_uri)
        return self.ledger



    def create(self, args):
        try:
            self.askpass = args.p
        except AttributeError:
            pass

        self.wallet = DemoWallet()
        self.create_store(args, store_scope='key')
        keyring = args.keyring
        if keyring == None:
            if self.cfg.true('WALLET_SYSTEM_KEYRING'):
                keyring = self.cfg.get('WALLET_SYSTEM_KEYRING_DOMAIN')
        if keyring != None:
            self.keyring = KeyringStore(keyring, self.db)
        passphrase = self.getpw()
        if passphrase != '':
            passphrase_confirm = self.getpw()
            if passphrase != passphrase_confirm:
                raise ValueError('Passphrase mismatch')
        else:
            passphrase = None
        if self.keyring:
            self.keyring.add_key(self.wallet, passphrase=passphrase, opslimit=int(self.cfg.get('WALLET_OPSLIMIT')), memlimit=int(self.cfg.get('WALLET_MEMLIMIT')))
        else:
            self.keystore.add_key(self.wallet, passphrase=passphrase, opslimit=int(self.cfg.get('WALLET_OPSLIMIT')), memlimit=int(self.cfg.get('WALLET_MEMLIMIT')))


    # TODO: split up args processing in separate functions
    def init(self, args=None, store_scope=None, create=False):
        #v = None
        identity = None
        if args != None:
            if args.pubkey != None:
                identity = UsawaUser(pubkey=bytes.fromhex(args.pubkey))
            else:
                self.cfg.get('WALLET_IDENTITY')

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
        self.set('ledger_path', self.ledger_path_in)
        self.create_store(args, store_scope=store_scope, create_ledger=create)
        self.create_resolver()
        self.load_accounts()

        try:
            self.askpass = args.p
        except AttributeError:
            pass

        keyring = args.keyring
        if keyring == None:
            if self.cfg.true('WALLET_SYSTEM_KEYRING'):
                keyring = self.cfg.get('WALLET_SYSTEM_KEYRING_DOMAIN')
        if keyring != None:
            self.keyring = KeyringStore(keyring, self.db)
            logg.debug('using keyring {}'.format(self.keyring))

        if self.idgetter != None:
            identity = self.idgetter()
        self.load_wallet(identity=identity, signing=self.signing)

        if self.replay:
            self.store.load()
            self.ledger.truncate()
            logg.debug('replayed ledger {}'.format(self.ledger.to_string()))


    def commit(self, ledger=None):
        if ledger == None:
            ledger = self.ledger
        ledger.truncate()
        ledger.sign()
        self.store.save_state()
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


    def check_wallet(self):
        if self.wallet != None:
            return True
        self.keystore.get_default_key(DemoWallet)
        return True


    # TODO: Instantiate user earlier from explicit config identity
    def load_wallet(self, signing=False, identity=None, replace=False):
        pubkey = None
        if identity != None:
            pubkey = identity.pubkey
        elif self.wallet != None:
            pubkey = self.wallet.pubkey()
            identity = UsawaUser(pubkey=pubkey)
        #    pubkey = self.cfg.get("WALLET_IDENTITY")
        #    try:
        #        pubkey = bytes.fromhex(pubkey)
        #    except TypeError:
        else:
            o = self.keystore.get_default_key(DemoWallet)
            pubkey = o.pubkey()
            identity = UsawaUser(pubkey=pubkey)
            logg.debug('using default identity {}'.format(identity))
        if self.wallet != None and not replace:
            raise AttributeError('wallet set')
        if not self.signing and not signing:
            self.wallet = self.keystore.get_default_key(DemoWallet)
        elif not signing:
            self.wallet = self.keystore.get_default_key(DemoWallet)
        else:
            ops = int(self.cfg.get('WALLET_OPSLIMIT', 0))
            mem = int(self.cfg.get('WALLET_MEMLIMIT', 0))
            if self.keyring != None:
                self.wallet = self.keyring.get_key(DemoWallet, pubkey=identity.pubkey, opslimit=ops, memlimit=mem)
            if self.wallet == None:
                logg.debug('decrypting wallet for user {}'.format(identity))
                pw = self.getpw()
                self.wallet = self.keystore.get_key(DemoWallet, pubkey=pubkey, passphrase=pw, opslimit=ops, memlimit=mem)

            logg.debug('have wallet {}'.format(self.wallet))
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


    def create_store(self, args, store_scope=None, create_ledger=False):
        # TODO: done twice
        topic = parse_topic(self.cfg.get('LEDGER_TOPIC'))
        #if topic != None:
        #    topic = parse_topic(topic)
        #logg.debug('create store {}'.format(topic))
        if store_scope == None:
            store_scope = 'ledger'
        if self.store != None:
            raise AttributeError('store set')
        if store_scope  == 'ledger':
            if self.ledger == None:
                if not bool(topic):
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
            if self.ledger:
                logg.debug('using preloaded ledger for store {}'.format(self.ledger))
                self.store = LedgerStore(self.db, self.ledger)
            else:
                try:
                    self.store = LedgerStore.from_state(self.db, topic)
                    self.ledger = self.store.ledger
                    self.uidx = self.ledger.uidx
                except FileNotFoundError:
                    if create_ledger:
                        self.ledger_from_args(args)
                        self.store = LedgerStore(self.db, self.ledger)
                    else:
                        logg.exception('ledger missing and not creating')
            self.keystore = self.store
        elif store_scope == 'asset' or store_scope == 'entry' or store_scope == 'key':
            self.keystore = KeyStore(self.db)
            if store_scope == 'asset':
                self.store = AssetStore(self.db)
            elif store_scope == 'entry':
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
