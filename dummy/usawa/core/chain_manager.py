import os
import logging
from usawa import Ledger,  load
from usawa.crypto import ACL, DemoWallet
from usawa.store import LedgerStore
from whee.valkey import ValkeyStore
import os
import shutil
import logging

from usawa import Ledger, load

logg = logging.getLogger("core.chain_manager")


def default_chain_dir():
    """Return the conventional XDG data directory for usawa ledger files.
    
    Defaults to ~/.local/share/usawa/ledger/ unless XDG_DATA_HOME is set.
    Directory is created if it does not exist.
    """
    xdg_data = os.environ.get(
        'XDG_DATA_HOME',
        os.path.join(os.path.expanduser('~'), '.local', 'share'),
    )
    path = os.path.join(xdg_data, 'usawa', 'ledger')
    os.makedirs(path, exist_ok=True)
    return path


class LedgerChainManager:

    def __init__(self, genesis_path=None):
        """Initialise the chain manager.

        On first ever launch, supply genesis_path so it can be copied into
        the conventional directory as 0.xml.  On subsequent launches, omit
        genesis_path — the manager will reconstruct the chain from disk.

        :param genesis_path: Path to the genesis XML file (optional after first run)
        :type genesis_path: str or None
        """
        self.basedir = default_chain_dir()
        logg.debug('chain dir: {}'.format(self.basedir))

        zero = os.path.join(self.basedir, '0.xml')
        if not os.path.exists(zero):
            if genesis_path is None:
                raise FileNotFoundError(
                    'no chain found in {} and no genesis_path provided'.format(self.basedir)
                )
            genesis_path = os.path.realpath(genesis_path)
            if not os.path.exists(genesis_path):
                raise FileNotFoundError('genesis file not found: {}'.format(genesis_path))
            shutil.copy(genesis_path, zero)
            logg.debug('copied genesis {} → {}'.format(genesis_path, zero))

        self.chain = self._reconstruct_chain()
        logg.debug('chain reconstructed with depth {}'.format(self.depth()))


    def _reconstruct_chain(self):
        """Rebuild the chain list by scanning sequential xml files on disk.

        Starts at 0.xml and stops at the first missing index.
        """
        chain = []
        index = 0
        while True:
            path = os.path.join(self.basedir, '{}.xml'.format(index))
            if not os.path.exists(path):
                break
            chain.append(path)
            index += 1
        if not chain:
            raise FileNotFoundError('no chain files found in: {}'.format(self.basedir))
        return chain


    def current(self):
        """Return the path of the most recent XML file in the chain."""
        return self.chain[-1]


    def derive_next(self):
        """Derive the next output file path based on the current chain length.

        genesis = index 0, first entry output = index 1, and so on.
        """
        next_index = len(self.chain)
        basename = '{}.xml'.format(next_index)
        return os.path.join(self.basedir, basename)


    def advance(self, written_path):
        """Call this after successfully writing an entry output file.

        Verifies the file exists before appending to the chain.
        """
        written_path = os.path.realpath(written_path)
        if not os.path.exists(written_path):
            raise FileNotFoundError(
                'written file not found, cannot advance chain: {}'.format(written_path)
            )
        self.chain.append(written_path)
        logg.debug('chain advanced to: {}'.format(written_path))


    def load_current(self):
        """Load and return a fresh Ledger instance from the current chain tail."""
        ledger_path = self.current()
        ledger_tree = load(ledger_path)
        ledger = Ledger.from_tree(ledger_tree)
        logg.debug('loaded ledger from: {}'.format(ledger_path))
        return ledger


    def write_entry(self, entry, ledger, store, wallet):
        """Sign and write an entry, then advance the chain.

        Encapsulates the full write sequence:
          entry.sign → store.add_entry → ledger.truncate → ledger.sign → write file
        """
        next_path = self.derive_next()

        raise NotImplementedError('not sure if we need this')
        db = ValkeyStore('')
    
        store = LedgerStore(db, ledger)
        pk = store.get_key()
        wallet = DemoWallet(privatekey=pk)
        logg.debug("wallet pk: %s pubk: %s", wallet.privkey().hex(), wallet.pubkey().hex())
        ledger.set_wallet(wallet)


        ledger.acl = ACL.from_wallet(wallet)
        self.ledger = ledger

        entry.sign(wallet)
        store.add_entry(entry, update_ledger=True)
        ledger.truncate()
        ledger.sign()

        with open(next_path, 'wb') as f:
            f.write(ledger.to_string())
        logg.debug('entry written to: {}'.format(next_path))

        self.advance(next_path)
        return next_path


    def depth(self):
        """Return the number of files in the chain including genesis."""
        return len(self.chain)


    def __repr__(self):
        return 'LedgerChainManager(depth={}, current={})'.format(self.depth(), self.current())
