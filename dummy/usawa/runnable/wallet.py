import argparse
import getpass
import logging
import os
import sys
#from pathlib import Path

#from nacl.signing import SigningKey
#from nacl.secret import SecretBox
#from nacl.pwhash import argon2i
#from whee.valkey import ValkeyStore
#from whee.fs import FsStore
#from xdg_base_dirs import xdg_data_home

#from usawa.store import KeyStore
from usawa.context import UsawaContext
from usawa.crypto import DemoWallet
from usawa.config import load_config

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

#PRIVATEKEY_FILE = "privatekey.box"
#PUBLICKEY_FILE = "publickey.bin"

# TODO: change to xdg_data_dir
#DEFAULT_WALLET_DIR = (
#    Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "usawa"
#)


#def encrypt_seed(seed: bytes, passphrase: str) -> bytes:
#    salt = os.urandom(argon2i.SALTBYTES)
#    key = argon2i.kdf(
#        SecretBox.KEY_SIZE,
#        passphrase.encode(),
#        salt,
#    )
#    box = SecretBox(key)
#    encrypted = box.encrypt(seed)
#
#    # Prepend salt so we can re-derive the key on decrypt
#    return salt + encrypted
#
#
#def setup_wallet(cfg, wallet_dir=None):
#    db = None
#    store_type = cfg.get('STORE_TYPE')
#    if store_type == 'valkey':
#            db = ValkeyStore(
#                "",
#                host=cfg.get("VALKEY_HOST"),
#                port=cfg.get("VALKEY_PORT"),
#            )
#    elif store_type == 'fs':
#        db = FsStore(
#            base=cfg.get('FSSTORE_BASE', xdg_data_home()),
#            dbname='usawa',
#            )
#    else:
#        raise ValueError('invalid store type: ' + store_type)
#
#    store = KeyStore(db)
#
#    wallet_dir = Path(wallet_dir) if wallet_dir else DEFAULT_WALLET_DIR
#    wallet_dir.mkdir(parents=True, exist_ok=True)
#    logg.info("wallet directory: %s", wallet_dir)
#
#    privatekey_path = wallet_dir / PRIVATEKEY_FILE
#    publickey_path = wallet_dir / PUBLICKEY_FILE
#
#    passphrase = getpass.getpass("Enter wallet passphrase: ")
#    passphrase_confirm = getpass.getpass("Confirm wallet passphrase: ")
#    if passphrase != passphrase_confirm:
#        logg.error("passphrases do not match")
#        return 1
#
#    random_bytes = os.urandom(32)
#    logg.debug("generated 32-byte seed")
#
#    encrypted = encrypt_seed(random_bytes, passphrase)
#    with open(privatekey_path, "wb") as f:
#        f.write(encrypted)
#    logg.info("encrypted key material saved to: %s", privatekey_path)
#
#    sk = SigningKey(random_bytes)
#    pk = sk.verify_key
#    with open(publickey_path, "wb") as f:
#        f.write(pk.encode())
#    logg.info("public key saved to: %s", publickey_path)
#    ops = int(cfg.get('WALLET_OPSLIMIT', 0))
#    mem = int(cfg.get('WALLET_MEMLIMIT', 0))
#
#    wallet = DemoWallet(privatekey=random_bytes)
#    store.add_key(wallet, passphrase=passphrase_confirm, opslimit=ops, memlimit=mem)
#    logg.info("key written to store")
#
#    logg.info("setup complete.")
#    logg.info("your 32-byte public key (hex): %s", pk.encode().hex())
#
#    return 0
#

def main():
    argp = argparse.ArgumentParser()
    argp.add_argument('-c', type=str, help='override config dir')
    argp.add_argument('-v', type=str, choices=['info','debug','warning','error'], help='be verbose')
    argp.add_argument('--default', action='store_true', help='use as default key')
    args = argp.parse_args()

    if args.v:
        logg.setLevel(getattr(logging, args.v.upper()))

    cfg = load_config(config_dir=args.c)
#    setup_wallet(cfg)

    ctx = UsawaContext(cfg)
    ctx.create_store(args, store_scope='key')
    wallet = DemoWallet()

    passphrase = None
    if not cfg.true('WALLET_SYSTEM_KEYRING'):
        passphrase = getpass.getpass("Enter wallet passphrase: ")
        passphrase_confirm = getpass.getpass("Confirm wallet passphrase: ")
        if passphrase != passphrase_confirm:
            logg.error("passphrases do not match")
            sys.exit(1)
    ctx.keystore.add_key(wallet, passphrase=passphrase, opslimit=int(cfg.get('WALLET_OPSLIMIT')), memlimit=int(cfg.get('WALLET_MEMLIMIT')))


if __name__ == '__main__':
    main()
