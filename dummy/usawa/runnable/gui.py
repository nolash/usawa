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
    argp.add_argument('-c', type=str, help='override config dir')
    argp.add_argument('-i', type=str, help='input ledger state')
    argp.add_argument('-v', type=str, choices=['info','debug','warning','error'], help='be verbose')
    args = argp.parse_args()

    if args.v:
        logg.setLevel(getattr(logging, args.v.upper()))

    cfg = usawa.config.load_config(config_dir=args.c) 
    ctx = UsawaContext(cfg, signing=False, pwgetter=emptypw)
    ctx.init(args)
    ctx.askpass = True

    app = Usawa(ctx, application_id='org.usawa.app')
    app.run(sys.argv)


if __name__ == '__main__':
    main()
