import logging

from usawa.account import Account

logg = logging.getLogger('usawa.index.account')



class EntryAccountIndex:

    def __init__(self):
        self.idx = {}
        self.c = -1
        self.v = None
        self.it = None
        self.k = None


    def entry_callback(self, entry):
        idx = {}
        for ls in [entry.srcs, entry.dsts]:
            for o in ls:
                account_path = o.account_path()
                try:
                    account = idx[account_path]
                except KeyError:
                    logg.debug('path ' + account_path)
                    account = Account.from_path(account_path)
                    idx[account_path] = account
        for k in idx.keys():
            try:
                self.idx[k]
            except KeyError:
                self.idx[k] = []
            self.idx[k].append(entry.serial)
            logg.debug('indexed {} -> {}'.format(k, entry.serial))
        return True


    def start(self, k):
        self.k = k
        return self.__iter__()


    def __iter__(self):
        self.v = self.idx[self.k]
        self.c = 0
        return self


    def __next__(self):
        v = None
        try:
            v = self.v[self.c]
        except IndexError:
            self.k = None
            self.c = -1
            self.v = None
            self.it = None
            raise StopIteration()
        self.c += 1

        return v
