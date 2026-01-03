import os
import datetime

import lxml

from .constant import NAMESPACES

XML_FORMAT_VERSION = 1

script_dir = os.path.realpath(os.path.dirname(__file__))


def nsmap():
    """Namespaces to use in ledger XML tree operations.
    """
    return NAMESPACES


def parse(v):
    """Parse ledger XML tree from XML string.
    """
    return lxml.etree.fromstring(v)


def dump(v):
    """Generate XML string from ledger XML tree.
    """
    return lxml.etree.tostring(v)
