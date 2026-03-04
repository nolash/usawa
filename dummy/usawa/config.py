import os
import confini
from xdg.BaseDirectory import save_data_path
import logging

__datadir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")
logger = logging.getLogger(__name__)

def load():
    cfg = confini.Config(__datadir)
    cfg.process()

    if "SERVER_SOCKET_FILE_PATH" in cfg.store:
        socket_file_path = cfg.get("SERVER_SOCKET_FILE_PATH")
    else:
        socket_file_path = save_data_path("usawa")
        cfg.add(socket_file_path, "SERVER_SOCKET_FILE_PATH")

    if "SIGS_DEFAULT_PUBLIC_KEY" in cfg.store:
        default_public_key = cfg.get("SIGS_DEFAULT_PUBLIC_KEY")
    else:
        default_public_key = save_data_path("usawa")
        cfg.add(default_public_key, "SIGS_DEFAULT_PUBLIC_KEY")

    return cfg