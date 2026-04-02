import enum
import logging
import re

from .error import AccountError

logg = logging.getLogger('account')


def check_path_parts(path):
    parts = path.split('/')
    for v in parts:
        if not v.isalnum():
            raise AccountError('invalid part: {} ({})'.format(v, v.encode('utf-8').hex()))
    #return True
    typ = getattr(AccountType, parts[0].lower())
    return (typ, parts[1:],)


def from_account_path(p, sym=None, typ=None):
    if sym != None:
        p = sym + '.' + p
    o = p.split('.')
    if len(o) != 2:
        raise ValueError('account path should have zero or one symbol specifier')
    sym = o[0]
    if typ == None:
        o = check_path_parts(o[1])
        typ = o[0]
        path = o[1]
    else:
        path = o[1].split('/')

    return (sym, typ, path,)


class AccountType(enum.Enum):
    liability = 'Liability'
    asset = 'Asset'
    income = 'Income'
    expense = 'Expense'
    imprt = 'Import'
    export = 'Export'
    equity = 'Equity'


class AccountDisplay(enum.IntEnum):
    full = 0
    typ = 1
    path = 2


class Account:

    path_parser = from_account_path

    def __init__(self, sym, typ, segments):
        if not isinstance(typ, AccountType):
            raise ValueError('invalid account type: ' + typ)
        self.sym = sym
        self.typ = typ
        if isinstance(segments, str):
            segments = [segments]
        self.segments = segments


    @staticmethod
    def from_path(path, sym=None, typ=None):
        o = Account.path_parser(path, sym=sym, typ=typ)
        return Account(o[0], o[1], o[2])


    def to_path(self, display=AccountDisplay.full):
        path = '/'.join(self.segments)
        if display == AccountDisplay.full:
            path = '{}.{}/{}'.format(self.sym, self.typ.value.lower(), path)
        elif display == AccountDisplay.typ:
            path = '{}/{}'.format(self.typ.value.lower(), path)
        return path


    def __str__(self):
        return self.to_path()


class AccountIndex:

    def __init__(self, unitindex): #, pathvalidator=default_check):
        self.uidx = unitindex
        self.accounts = {}
        self.locked = False
        #self.validate = pathvalidator
        self.iterval = None
        self.iterfilter = None


#    @staticmethod
#    def from_io(self, io, closer=None):
#        while True:
#            v = io.readline()
#        if closer != None:
#            closer()
#

    @staticmethod
    def from_file(unitindex, filepath):
        o = AccountIndex(unitindex)
        f = open(filepath, "r")
        while True:
            v = f.readline()
            if not v:
                break
            o.add(v.strip())
        f.close()
#        return AccountIndex.from_io(f, closer=f.close) 
        return o


    def add(self, path, sym=None, typ=None):
        account = Account.from_path(path, sym=sym, typ=typ)
        try:
            sym = self.uidx.sym(account.sym)
        except KeyError:
            raise AccountError('unknown unit ' + sym)
        if self.locked:
            raise AccountError('account index locked')
        if self.accounts.get(sym) == None:
            self.accounts[sym] = []
        elif path in self.accounts[sym]:
            logg.debug('Ignoring duplicate account: {}:{}'.format(sym, path))
        path = account.to_path()
        logg.info('add account {}'.format(path))
        self.accounts[sym].append(path)
        return account


    def lock(self):
        self.locked = True


    def check(self, sym, typ, path):
        s = '{}.{}/{}'.format(sym, typ.value.lower(), path)
        r = False
        try:
            r = s in self.accounts[sym]
        except KeyError:
            return None
        return s


    def check_path(self, path):
        o = Account.path_parser(path)
        return self.check(o[0], o[1], o[2])


    def set_filter(self, sym=None, typ=None, path=None, display=AccountDisplay.full):
        if typ != None:
            typ = typ.value
        self.iterfilter = (sym, typ, path, display,)


    def reset_filter(self):
        self.iterfilter = None


    def __iter__(self, fltr=None):
        self.iterval = None
        keys = list(self.uidx.syms())
        keys.sort()
        fltr = self.iterfilter
        for k in keys:
            if fltr != None:
                if fltr[0] != None:
                    if fltr[0] != k:
                        continue
            accounts = self.accounts.get(k)
            if accounts == None:
                continue
            for v in accounts:
                path = v
                (sym, v) = v.split('.', maxsplit=1)
                (typ, v) = v.split('/', maxsplit=1)
                if fltr != None:
                    if fltr[1] != None:
                        if typ.casefold() != fltr[1].casefold():
                            continue
                    if fltr[2] != None:
                        if not re.search(fltr[2], v, re.IGNORECASE):
                            continue
                if self.iterval == None:
                    self.iterval = []
                if fltr != None:
                    if fltr[3] != AccountDisplay.full:
                        path = v
                        if fltr[3] == AccountDisplay.typ:
                            path = typ + '/' + path 
                self.iterval.append(path)
        return self


    def __next__(self):
        if self.iterval == None:
            raise StopIteration()
        if len(self.iterval) == 0:
            self.iterval = None
            raise StopIteration()
        v = self.iterval.pop(0)
        return v
