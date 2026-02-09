import logging

import rencode
import lxml.etree

from .constant import NSPREFIX
from .xml import nsmap


logg = logging.getLogger('usawa.unit')


class UnitIndex:

    default_precision = 2
    default_unit = 'BTC'

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
        self.exchange = {base: 1000000000}


    """Add a unit to the index.

    The exchange rate is stored as an integer with nano precision. If a float is passed as value, it will be correspondingly converted to an integer.

    :param sym: The symbol name of the unit.
    :type sym: str
    :param precision: The decimal precision of the base unit. Default is 2.
    :type precision: int
    :param ex: The exchange rate of the unit, relative to the base unit. Default is 1000000000 (1.0).
    :type ex: int or float
    """
    def add(self, sym, precision=2, ex=1000000000):
        self.detail[sym] = precision
        if isinstance(ex, float):
            ex = int(ex*1000000000) # nano resolution
        self.exchange[sym] = ex


    """Create a unit index object from XML.

    The XML element expected is ledger/units.

    :param tree: XML tree.
    :type tree: lxml.etree.Element
    :returns: The unit index object.
    :rtype: usawa.UnitIndex
    """
    @staticmethod
    def from_tree(tree):
        if tree.tag == 'ledger':
            tree = tree.find('units', namespaces=nsmap())
        logg.debug('unit index tag ' + tree.tag)
        base = tree.get('base')
        r = UnitIndex(base)
        for o in tree.iter(NSPREFIX + 'unit'):
            logg.debug('add unit ' + o.get('sym'))
            r.detail[o.get('sym')] = int(o.find('precision', namespaces=nsmap()).text)
            r.exchange[o.get('sym')] = int(o.find('exchange', namespaces=nsmap()).text)
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

    The value represents a decimal number with nano precision. For example, a value of 4200000000 corresponds to a float value of 4.2.

    :raises: KeyError if symbol not found.
    :returns: Rate
    :rtype: int
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

        v = s[:i]
        r = s[i:]
        if self.detail[sym] > 0:
            if len(v) == 0:
                v = '0'
            r = v + '.' + s[i:]
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

    def to_list(self):
        syms = list(self.detail.keys())
        syms.sort()
        units = []
        for v in syms:
            precision = self.detail[v].to_bytes(1)
            exchange = self.exchange[v].to_bytes(8, byteorder='big')
            units.append((v, precision, exchange,))
        d = [
            self.base,
            units,
                ]
        return d


    def serialize(self):
        d = self.to_list() 
        return rencode.dumps(d)


    @staticmethod
    def deserialize(v):
        pass


    """Generate XML tree from current state of the object.

    The XML element generated is the units sub-element of the root ledger element.
    :returns: XML tree
    :rtype: lxml.etree.Element
    """
    def to_tree(self):
        tree = lxml.etree.XML('<units></units>')
        tree.set('base', self.base)
        for k in self.detail.keys():
            unit = lxml.etree.SubElement(tree, 'unit')
            unit.set('sym', k)
            o = lxml.etree.SubElement(unit, 'precision')
            o.text = str(self.detail[k])
            unit.append(o)
            o = lxml.etree.SubElement(unit, 'exchange')
            o.text = str(self.exchange[k])
            unit.append(o)
            tree.append(unit)

        return tree
