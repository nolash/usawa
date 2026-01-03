import logging

from .constant import NSPREFIX
from .xml import nsmap

logg = logging.getLogger('usawa.unit')

BASE_UNIT = 'BTC'


class UnitIndex:
    """UnitIndex holds metadata for units of account.

    Specifically, it defines an exchange rate aswell as decimal precision.

    The index is instantiated with a base unit. All exchange rates are relative to the base unit.

    :param base: The base unit of the index.
    :type base: str
    :param precision: The decimal precision of the base unit. Default is 2.
    :type precision: int
    """
    def __init__(self, base, precision=2):
        self.base = base
        self.detail = {base: precision}
        self.exchange = {base: 1}


    """Add a unit to the index.

    :param sym: The symbol name of the unit.
    :type sym: str
    :param precision: The decimal precision of the base unit. Default is 2.
    :type precision: int
    :param ex: The exchange rate of the unit, relative to the base unit. Default is 1.0.
    :type ex: float
    """
    def add(self, sym, precision=2, ex=1.0):
        self.detail[sym] = precision
        self.exchange[sym] = ex


    """Create a unit index from a full ledger XML tree.

    :param tree: Parsed and verified XML tree.
    :type tree: lxml.etree.ElementTree
    :returns: The unit index object.
    :rtype: usawa.UnitIndex
    """
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


    """Verify whether the unit index is ready for use.

    :raises: KeyError if symbol not found.
    :returns: Itself.
    :rtype: usawa.UnitIndex
    """
    def check(self):
        self.get(self.base)
        return self


    """Retrieve the precision for the unit.

    :param k: Unit symbol.
    :type k: str
    :raises: KeyError if symbol not found.
    :returns: The decimal precision.
    :rtype: int
    """
    def get(self, k):
        return self.detail[k]


    """Check whether symbol exists in index.

    :raises: KeyError if symbol not found.
    :returns: Symbol
    :rtype: str
    """
    def sym(self, k):
        _ = self.get(k)
        return k


    """Retrieve the exchange rate for the unit.

    :raises: KeyError if symbol not found.
    :returns: Rate
    :rtype: float
    """
    def ex(self, k):
        return self.exchange[k]


    """Retrieve a list of all the units in the index.

    :returns: The list of symbols.
    :rtype: list of str
    """
    def syms(self):
        return list(self.detail.keys())


    """Generate a string representing the decimal equivalent of the value to the precision of the unit.

    :param sym: The symbol to use precision for.
    :type sym: str
    :param v: The value amount to generate the string for.
    :type v: int
    :param allow_negative: If True, fail if v is negative.
    :type allow_negative: boolean
    :raises: ValueError on illegal negative value.
    :raises: KeyError if symbol not in index.
    :returns: The decimal string.
    :rtype: str
    :todo: Rename to to_decimalstring
    """
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

    """Generate an integer value from a decimal string, including all decimal values.

    Ensures that the correct number of decimals are added to the integer, even if the string does not contain all of the decimal digits. For example: A symbol with precision 3 and string value 1.23 will return 1230

    :param sym: The symbol to use precision for.
    :type sym: str
    :param v: The decimal value string to convert.
    :type v: str
    :param allow_negative: If True, fail if v represents a negative value.
    :type allow_negative: boolean
    :raises: ValueError on illegal negative value.
    :raises: KeyError if symbol not in index.
    :returns: The integer with full decimal precision.
    :rtype: int
    :todo: Rename to to_decimalstring
    """
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
