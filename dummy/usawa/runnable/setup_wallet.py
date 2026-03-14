import getpass
import logging
import os
from pathlib import Path
from nacl.signing import SigningKey
from nacl.secret import SecretBox
from nacl.pwhash import argon2i

logg = logging.getLogger("core.setup_wallet")

PRIVATEKEY_FILE = "privatekey.box"
PUBLICKEY_FILE = "publickey.bin"

DEFAULT_WALLET_DIR = (
    Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "usawa"
)


def encrypt_seed(seed: bytes, passphrase: str) -> bytes:
    salt = os.urandom(argon2i.SALTBYTES)
    key = argon2i.kdf(
        SecretBox.KEY_SIZE,
        passphrase.encode(),
        salt,
    )
    box = SecretBox(key)
    encrypted = box.encrypt(seed)

    # Prepend salt so we can re-derive the key on decrypt
    return salt + encrypted


def setup_wallet(wallet_dir=None):
    wallet_dir = Path(wallet_dir) if wallet_dir else DEFAULT_WALLET_DIR
    wallet_dir.mkdir(parents=True, exist_ok=True)
    logg.info("wallet directory: %s", wallet_dir)

    privatekey_path = wallet_dir / PRIVATEKEY_FILE
    publickey_path = wallet_dir / PUBLICKEY_FILE

    passphrase = getpass.getpass("Enter wallet passphrase: ")
    passphrase_confirm = getpass.getpass("Confirm wallet passphrase: ")
    if passphrase != passphrase_confirm:
        logg.error("passphrases do not match")
        return 1

    random_bytes = os.urandom(32)
    logg.debug("generated 32-byte seed")

    encrypted = encrypt_seed(random_bytes, passphrase)
    with open(privatekey_path, "wb") as f:
        f.write(encrypted)
    logg.info("encrypted key material saved to: %s", privatekey_path)

    sk = SigningKey(random_bytes)
    pk = sk.verify_key
    with open(publickey_path, "wb") as f:
        f.write(pk.encode())
    logg.info("public key saved to: %s", publickey_path)

    logg.info("setup complete.")
    logg.info("your 32-byte public key (hex): %s", pk.encode().hex())

    return 0
