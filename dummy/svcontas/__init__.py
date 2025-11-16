from lxml import etree

from .ledger import Ledger
from .entry import Entry, EntryPart
from .crypto import DemoWallet, ACL
#from .state import State
from .xml import nsmap
from .unit import UnitIndex


def init_ledger(tree, units, acl=None):
    return Ledger.from_tree(tree, units, acl=acl)
    

def get_units(tree):
    o = tree.find('units', namespaces=nsmap())
    return UnitIndex.from_tree(o)


def load(fp):
    f = open(fp, 'r')
    tree = etree.parse(f)
    f.close()
    return tree.getroot()
