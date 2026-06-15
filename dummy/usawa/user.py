class UsawaUser:

    def __init__(self, uid=None, uname=None, displayname=None, pubkey=None):
        self.uid = uid
        self.uname = uname
        self.displayname = displayname
        self.pubkey = pubkey
        self.ledger = None


    def __str__(self):
        return "{} ({}) pubkey: {}".format(self.uname, self.uid, self.pubkey)
