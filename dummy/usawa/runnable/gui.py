import logging
import sys
import argparse

from usawa.gui import Usawa
import usawa.config
from usawa.context import UsawaContext

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()


def emptypw():
    return ''


def main():
    argp = argparse.ArgumentParser()
    argp.add_argument('-t', dest="topic", type=str, help='ledger topic')
    argp.add_argument('-c', type=str, help='override config dir')
    argp.add_argument('-i', type=str, help='input ledger state')
    argp.add_argument('-v', type=str, choices=['info','debug','warning','error'], help='be verbose')
    argp.add_argument('-k', type=str, dest='pubkey', help='public key identity to use for signing')
    argp.add_argument('-y', '--with-keyring', type=str, dest='keyring', help='use keyring with given usawa identifier')
    args = argp.parse_args()

    if args.v:
        logg.setLevel(getattr(logging, args.v.upper()))

    cfg = usawa.config.load_config(config_dir=args.c, topic=args.topic)
    signing = False
    if args.keyring != None:
        signing=True
    ctx = UsawaContext(cfg, signing=signing, pwgetter=emptypw)
    ctx.init(args)
    if args.keyring == None:
        ctx.askpass = True

    app = Usawa(ctx, application_id='org.usawa.app')
    app.run(sys.argv)


if __name__ == '__main__':
    main()
