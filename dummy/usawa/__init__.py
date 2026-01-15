import os

from lxml import etree

from .ledger import Ledger
from .entry import Entry, EntryPart
from .crypto import DemoWallet, ACL
from .xml import nsmap
from .unit import UnitIndex


data_dir = os.path.join(os.path.dirname(__file__), 'data')
schema_path = os.path.join(data_dir, 'schema.xsd')

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
