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


def main():
    argp = argparse.ArgumentParser()
    argp.add_argument('-c', type=str, help='override config dir')
    argp.add_argument('-v', type=str, choices=['info','debug','warning','error'], help='be verbose')
    argp.add_argument('-p', action='store_true', help='use passphrase to encrypt local store copy')
    argp.add_argument('-y', '--with-keyring', type=str, dest='keyring', help='use keyring with given usawa identifier')
    argp.add_argument('--default', action='store_true', help='use as default key')
    args = argp.parse_args()

    if args.v:
        logg.setLevel(getattr(logging, args.v.upper()))

    cfg = load_config(config_dir=args.c)

    ctx = UsawaContext(cfg, signing=False)
    ctx.create(args)

    print(ctx.wallet.pubkey().hex())


if __name__ == '__main__':
    main()
