import os
import confini
from xdg.BaseDirectory import save_data_path
import logging

__datadir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")
logger = logging.getLogger(__name__)


def load():
    cfg = confini.Config(__datadir)
    cfg.process()

    if "VALKEY_HOST" in cfg.store:
        valkey_host = cfg.get("VALKEY_HOST")
    else:
        valkey_host = save_data_path("usawa")
        cfg.add(valkey_host, "VALKEY_HOST")

    if "VALKEY_PORT" in cfg.store:
        valkey_port = cfg.get("VALKEY_PORT")
    else:
        valkey_port = save_data_path("usawa")
        cfg.add(valkey_port, "VALKEY_PORT")

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

    if "SIGS_DEFAULT_PRIVATE_KEY" in cfg.store:
        default_private_key = cfg.get("SIGS_DEFAULT_PRIVATE_KEY")
    else:
        default_private_key = save_data_path("usawa")
        cfg.add(default_private_key, "SIGS_DEFAULT_PRIVATE_KEY")

    if "FS_RESOLVER_STORE_PATH" in cfg.store:
        fs_resolver_store_path = cfg.get("FS_RESOLVER_STORE_PATH")
    else:
        fs_resolver_store_path = save_data_path("usawa")
        cfg.add(fs_resolver_store_path, "FS_RESOLVER_STORE_PATH")

    return cfg
