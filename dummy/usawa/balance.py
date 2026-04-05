import logging

logg = logging.getLogger('usawa.balancer')


class Balancer:

    def __init__(self, unitindex, value=None):
        self.uidx = unitindex
        self.r = 0
        self.m = 0
        self.z = 0


    def apply_part(self, part):
        amount = self.uidx.val(part.unit, part.amount)
        fn = getattr(self, '_handle_' + part.typ)
        v = fn(amount[0], part.isdebit)
        self.z += abs(amount[0])
        logg.debug('after {} {} => {} = {}'.format(part.unit, part.amount, amount[0], self.r))


    def balanced(self):
        return self.r == 0


    def balance(self):
        return self.r


    def value(self):
        return int(self.z / 2)


    def _handle_income(self, amount, issrc=False):
        if not issrc:
            raise TypeError('income can only be src')
        self.r -= amount
        return amount


    def _handle_expense(self, amount, issrc=False):
        if issrc:
            raise TypeError('expense can only be dst')
        self.r += amount
        return amount

    
    def _handle_asset(self, amount, issrc=False):
        if issrc:
            if amount >= 0:
                raise ValueError('positive asset can only be dst')
        self.r += amount
        return amount


    def _handle_liability(self, amount, issrc=False):
        if issrc:
            if amount < 0:
                raise ValueError('negative liability can only be dst')
        self.r -= amount
        return amount
