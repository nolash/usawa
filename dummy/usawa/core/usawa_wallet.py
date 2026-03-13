import gnupg
import logging

from usawa.crypto import DemoWallet


logg = logging.getLogger("usawawallet")


class UsawaWallet(DemoWallet):

    def __init__(self, keyfile, gpgdir="~/.gnupg", passphrase=None):
        self.gpg = gnupg.GPG(gnupghome=gpgdir)
        self.keyfile = keyfile
        f = open(self.keyfile, "rb")
        pk = self.gpg.decrypt_file(f, passphrase=passphrase)
        f.close()
        logg.debug("decrypted pk with key {}".format(pk.key_id))
        super(UsawaWallet, self).__init__(privatekey=pk.data)
