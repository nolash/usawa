import logging

logg = logging.getLogger('usawa.balancer')


class Balancer:

    def __init__(self, unitindex):
        self.uidx = unitindex
        self.r = 0
        self.m = 0


    def apply_part(self, part):
        amount = self.uidx.val(part.unit, part.amount)
        fn = getattr(self, 'handle_' + part.typ)
        fn(amount[0], part.isdebit)
        self.m += amount[1]
        logg.debug('after {} {} => {} = {}'.format(part.unit, part.amount, amount[0], self.r))


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


#class Balancer:
#
#    def __init__(self, uidx, entry=None, base=None):
#        self.r = 0
#        self.uidx = uidx
#        self.max_precision = 0
#        self.ex = {}
#        self.running = {}
#        self.base = base
#        if entry != None:
#            self.scan(entry)
#            self.process_entry(entry)
#
#
#    def scan_units(self, uidx):
#        
#
#    def scan(self, entry):
#        base = None
#        for part in entry:
#            precision = self.uidx.get(part.unit)
#            if precision > self.max_precision:
#                self.max_precision = precision
#            self.ex[part.unit] = 1000000000
#            if base == None:
#                base = part.unit
#                continue
#            if base != part.unit:
#                if self.base == None:
#                    logg.warning('base is not set with entry with different units')
#        logg.debug('have max precision {}'.format(self.max_precision))
#        self.base = base
#
#
#    def init_unit(self, unit):
#        self.ex[unit] = 100000000
#        self.
#
#
#    def set_rate(self, unit, rate):
#        if unit == self.base:
#            raise ValueError('base rate against itself')
#        self.ex[unit] = rate
#
#
#    def process_entry(self, entry):
#        for part in entry:
#            self.apply_part(part)
#
#
#    def apply_part(self, part):
#        precision = self.uidx.get(part.unit)
#        mod = 10 ** (self.max_precision - precision)
#        amount = part.amount * mod
#        ex = self.ex[part.unit] / 1000000000
#        amount *= ex
#        fn = getattr(self, 'handle_' + part.typ)
#        fn(amount, part.isdebit)
#        logg.debug('after {} {} (ex {}) = {}'.format(part.unit, amount, ex, self.r))
#
#
#    def balanced(self):
#        return self.r == 0
#
#
#    def handle_income(self, amount, issrc=False):
#        if issrc:
#            self.r += amount
#        else:
#            self.r -= amount
#
#
#    def handle_expense(self, amount, issrc=False):
#        if issrc:
#            self.r -= amount
#        else:
#            self.r += amount
#
#    
#    def handle_asset(self, amount, issrc=False):
#        if issrc:
#            self.r += amount
#        else:
#            self.r -= amount
#
#
#    def handle_liability(self, amount, issrc=False):
#        if issrc:
#            self.r -= amount
#        else:
#            self.r += amount
