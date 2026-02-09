import os
import datetime

import lxml

from .constant import NAMESPACES

XML_FORMAT_VERSION = 1

script_dir = os.path.realpath(os.path.dirname(__file__))

"""Namespaces to use in ledger XML tree operations.
"""
def nsmap():
    return NAMESPACES

"""Parse ledger XML tree from XML string.
"""
def parse(v):
    return lxml.etree.fromstring(v)

"""Generate XML string from ledger XML tree.
"""
def dump(v):
    return lxml.etree.tostring(v)
