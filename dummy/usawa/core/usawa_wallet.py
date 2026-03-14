import logging
from usawa.crypto import DemoWallet

from nacl.secret import SecretBox
from nacl.pwhash import argon2i


logg = logging.getLogger("usawawallet")


class UsawaWallet(DemoWallet):
    def __init__(self, keyfile, passphrase=None):
        self.keyfile = keyfile

        with open(self.keyfile, "rb") as f:
            data = f.read()

        if passphrase is not None:
            # Extract salt and decrypt
            salt = data[: argon2i.SALTBYTES]
            encrypted = data[argon2i.SALTBYTES :]
            key = argon2i.kdf(
                SecretBox.KEY_SIZE,
                passphrase.encode(),
                salt,
            )
            box = SecretBox(key)
            try:
                seed = box.decrypt(encrypted)
            except Exception:
                raise ValueError("decryption failed: wrong passphrase?")
        else:
            seed = data

        if len(seed) != 32:
            raise ValueError("expected 32 bytes, got {}".format(len(seed)))

        logg.debug("wallet unlocked from keyfile")
        super(UsawaWallet, self).__init__(privatekey=seed)
