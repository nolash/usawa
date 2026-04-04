import logging

logg = logging.getLogger('usawa.balancer')


class Balancer:

    def __init__(self, unitindex, value=None):
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
