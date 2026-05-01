import os
import confini
import logging

__datadir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")
logger = logging.getLogger(__name__)


def load_config(config_dir=None, schemas=[]):
    cfg = confini.Config(__datadir, env_prefix="USAWA", override_dirs=config_dir or [])
    for v in schemas:
        cfg.add_schema_dir(v)
    cfg.censor("WALLET_KEY_PASSPHRASE")
    cfg.process()
    return cfg
