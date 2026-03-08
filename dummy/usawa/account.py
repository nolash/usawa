import logging

from .error import AccountError

logg = logging.getLogger('account')


def default_check(path):
    parts = path.split('.')
    for v in parts:
        if not v.isalnum():
            raise AccountError('invalid part: ' + v)
    return True


class AccountIndex:

    def __init__(self, unitindex, pathvalidator=default_check):
        self.uidx = unitindex
        self.accounts = {}
        self.locked = False
        self.validate = pathvalidator
        self.iterval = None


    def add(self, sym, path):
        try:
            sym = self.uidx.sym(sym)
        except KeyError:
            raise AccountError('unknown unit ' + sym)
        if self.locked:
            raise AccountError('account index locked')
        self.validate(path)
        if self.accounts.get(sym) == None:
            self.accounts[sym] = []
        elif path in self.accounts[sym]:
            logg.debug('Ignoring duplicate account: {}:{}'.format(sym, path))
        self.accounts[sym].append(path)


    def lock(self):
        self.locked = True


    def check(self, sym, path):
        try:
            return path in self.accounts[sym]
        except KeyError:
            return False


    def __iter__(self):
        keys = list(self.uidx.syms())
        keys.sort()
        for k in keys:
            for v in self.accounts[k]:
                if self.iterval == None:
                    self.iterval = []
                self.iterval.append(k + '/' + v)
        return self


    def __next__(self):
        if len(self.iterval) == 0:
            self.iverval = None
            raise StopIteration()
        v = self.iterval.pop(0)
        return v

