import logging

logg = logging.getLogger('usawa.balancer')


class Balancer:

    def __init__(self, unitindex):
        self.uidx = unitindex
        self.r = 0
        self.m = 0
        self.z = 0
        self.zsrc = 0
        self.zdst = 0


    def apply_part(self, part):
        amount = self.uidx.val(part.unit, part.amount)
        fn = getattr(self, '_handle_' + part.typ)
        fn(amount[0], part.isdebit)
        v = abs(amount[0])
        logg.debug('amount {} v {}'.format(amount, v))
        self.z += v
        self.m += amount[1]
        if part.isdebit:
            self.zsrc += v
        else:
            self.zdst += v
        logg.debug('after {} {} => {} = {}'.format(part.unit, part.amount, amount[0], self.r))


    def balanced(self):
        return self.r == 0


    def balance(self):
        return self.r


    def value(self):
        return int(self.z / 2)


    def src(self):
        return self.zsrc


    def dst(self):
        return self.zdst


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
