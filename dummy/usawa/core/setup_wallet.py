import getpass
import logging
import os
import subprocess
from nacl.signing import SigningKey


logg = logging.getLogger("core.setup_wallet")

GNUPG_DIR = "gnupg"
PRIVATEKEY_FILE = "privatekey.asc"
PUBLICKEY_FILE = "publickey.bin"


def _generate_gpg_key(gpg_dir, name, email, passphrase=None):
    env = {**os.environ, "GNUPGHOME": gpg_dir}

    subprocess.run(
        ["gpg-agent", "--homedir", gpg_dir, "--daemon"],
        capture_output=True,
        env=env,
    )

    batch_input = "\n".join(
        [
            "Key-Type: EdDSA",
            "Key-Curve: ed25519",
            "Subkey-Type: ECDH",
            "Subkey-Curve: cv25519",
            f"Name-Real: {name}",
            f"Name-Email: {email}",
            f"Passphrase: {passphrase}" if passphrase else "%no-protection",
            "%commit",
            "",
        ]
    )

    result = subprocess.run(
        ["gpg", "--homedir", gpg_dir, "--batch", "--gen-key"],
        input=batch_input.encode(),
        capture_output=True,
        env=env,
    )
    if result.returncode != 0:
        logg.error("key generation failed: %s", result.stderr.decode())
        return None

    list_result = subprocess.run(
        ["gpg", "--homedir", gpg_dir, "--with-colons", "--fingerprint", email],
        capture_output=True,
        env=env,
    )
    for line in list_result.stdout.decode().splitlines():
        if line.startswith("fpr"):
            return line.split(":")[9]
    return None


def setup_wallet():
    # Step 1 - Create gnupg dir
    gpg_dir = os.path.abspath(GNUPG_DIR)
    os.makedirs(gpg_dir, mode=0o700, exist_ok=True)
    logg.debug("gpg directory: %s", gpg_dir)

    env = {**os.environ, "GNUPGHOME": gpg_dir}

    # Step 2 - Prompt user
    name = input("Enter your name: ")
    email = input("Enter your email: ")
    passphrase = getpass.getpass("Enter wallet passphrase: ")

    # Step 3 - Generate keypair via subprocess
    fingerprint = _generate_gpg_key(gpg_dir, name, email, passphrase)
    if not fingerprint:
        logg.error("key generation failed")
        return 1
    logg.info("generated key fingerprint: %s", fingerprint)

    # Step 4 - Generate privatekey.asc (32 random bytes encrypted to GPG key)
    random_bytes = os.urandom(32)
    result = subprocess.run(
        [
            "gpg",
            "--homedir",
            gpg_dir,
            "--armor",
            "--encrypt",
            "--trust-model",
            "always",
            "-r",
            fingerprint,
        ],
        input=random_bytes,
        capture_output=True,
        env=env,
    )
    if result.returncode != 0:
        logg.error("encryption failed: %s", result.stderr.decode())
        return 1
    with open(PRIVATEKEY_FILE, "wb") as f:
        f.write(result.stdout)
    logg.info("private key material saved to: %s", PRIVATEKEY_FILE)

    # Step 5 - Derive public key
    sk = SigningKey(random_bytes)
    pk = sk.verify_key
    with open(PUBLICKEY_FILE, "wb") as f:
        f.write(pk.encode())
    logg.info("public key saved to: %s", PUBLICKEY_FILE)

    # Step 6 - Config summary
    logg.info("setup complete. add the following to your config:")
    logg.info("    gpg_dir = %s", gpg_dir)
    logg.info("public key (hex): %s", pk.encode().hex())

    return 0
