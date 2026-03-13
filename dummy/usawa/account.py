import enum
import logging

from .error import AccountError

logg = logging.getLogger('account')


def check_path_parts(path):
    parts = path.split('/')
    for v in parts:
        if not v.isalnum():
            raise AccountError('invalid part: ' + v)
    #return True
    typ = getattr(AccountType, parts[0].lower())
    return (typ, parts,)


def from_account_path(p, sym=None, typ=None):
    if sym != None:
        p = sym + '.' + p
    o = p.split('.')
    logg.debug('have {} {} {}'.format(p, sym, typ))
    if len(o) != 2:
        raise ValueError('account path should have zero or one symbol specifier')
    sym = o[0]
    o = check_path_parts(o[1])
    typ = o[0]
    path = o[1]

    return (sym, typ, path,)


class AccountType(enum.Enum):
    liability = 'Liability'
    asset = 'Asset'
    income = 'Income'
    expense = 'Expense'
    imprt = 'Import'
    export = 'Export'


class Account:

    path_parser = from_account_path

    def __init__(self, sym, typ, segments):
        if not isinstance(typ, AccountType):
            raise ValueError('invalid account type')
        self.sym = sym
        self.typ = typ
        self.segments = segments


    @staticmethod
    def from_path(path, sym=None, typ=None):
        o = Account.path_parser(path, sym=sym, typ=typ)
        return Account(o[0], o[1], o[2])


    def to_path(self):
        path = self.segments.join('/')
        path = '{}.{}/{}'.format(self.sym, self.typ, path)


class AccountIndex:

    def __init__(self, unitindex): #, pathvalidator=default_check):
        self.uidx = unitindex
        self.accounts = {}
        self.locked = False
        #self.validate = pathvalidator
        self.iterval = None


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

