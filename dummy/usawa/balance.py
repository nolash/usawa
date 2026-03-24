import logging

logg = logging.getLogger('usawa.balancer')


class Balancer:

    def __init__(self, uidx, entry, base=None):
        self.r = 0
        self.uidx = uidx
        self.max_precision = 0
        self.ex = {}
        self.base = base
        self.scan(entry)
        self.process(entry)


    def scan(self, entry):
        base = None
        for part in entry:
            precision = self.uidx.get(part.unit)
            if precision > self.max_precision:
                self.max_precision = precision
            self.ex[part.unit] = 1000000000
            if base == None:
                base = part.unit
                continue
            if base != part.unit:
                if self.base == None:
                    logg.warning('base is not set with entry with different units')
        logg.debug('have max precision {}'.format(self.max_precision))
        self.base = base


    def set_rate(self, unit, rate):
        if unit == self.base:
            raise ValueError('base rate against itself')
        self.ex[unit] = rate


    def process(self, entry):
        for part in entry:
            precision = self.uidx.get(part.unit)
            mod = 10 ** (self.max_precision - precision)
            amount = part.amount * mod
            ex = self.ex[part.unit] / 1000000000
            amount *= ex
            fn = getattr(self, 'handle_' + part.typ)
            fn(amount, part.isdebit)
            logg.debug('after {} {} (ex {}) = {}'.format(part.unit, amount, ex, self.r))


    def balanced(self):
        return self.r == 0


    def handle_income(self, amount, issrc=False):
        if issrc:
            self.r += amount
        else:
            self.r -= amount


    def handle_expense(self, amount, issrc=False):
        if issrc:
            self.r -= amount
        else:
            self.r += amount

    
    def handle_asset(self, amount, issrc=False):
        if issrc:
            self.r += amount
        else:
            self.r -= amount


    def handle_liability(self, amount, issrc=False):
        if issrc:
            self.r -= amount
        else:
            self.r += amount
