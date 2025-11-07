import logging

from .constant import NSPREFIX
from .xml import nsmap

logg = logging.getLogger('svcontas.unit')


class UnitIndex:

    def __init__(self, base):
        self.base = base
        self.detail = {}
        self.exchange = {}


    @staticmethod
    def from_tree(tree):
        r = UnitIndex(tree.get('base'))
        logg.debug('base {}'.format(tree))
        for o in tree.iter(NSPREFIX + 'unit'):
            logg.debug('add unit ' + o.get('sym'))
            r.detail[o.get('sym')] = int(o.find('precision', namespaces=nsmap()).text)
            r.exchange[o.get('sym')] = int(o.find('ex', namespaces=nsmap()).text)
        r.check()
        return r


    def check(self):
        self.get(self.base)
        return self


    def get(self, k):
        self.detail[k]
        return k


    def to_floatstring(self, sym, v, allow_negative=True):
        neg = v < 0
        if neg and not allow_negative:
            raise ValueError('negative value not allowed')
        v = abs(v)
        c = self.detail[sym]
        i = c * -1
        s = str(v)
        l = len(s)
        if l < c:
            ss = '0' * c
            s = '0' + ss[:c-l] + s
        r = s[:i] + '.' + s[i:]
        if neg:
            r = '-' + r
        return r


    def from_floatstring(self, sym, v, allow_negative=True):
        neg = False
        if v[0] == '-':
            if not allow_negative:
                raise ValueError('negative value not allowed')
            neg = True
            v = v[1:]
        c = self.detail[sym]
        s = v.split('.')
        if len(s) == 1:
            return int(s[0]) * (10**c)
        r = s[1]
        l = len(r)
        if l < c:
            r += '0' * (c - l)
        r = s[0] + r
        if neg:
            r *= -1
        return int(r)
