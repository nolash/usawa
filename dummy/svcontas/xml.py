import os
import datetime

import lxml

from .constant import NAMESPACES

script_dir = os.path.realpath(os.path.dirname(__file__))


def nsmap():
    return NAMESPACES


def parse(v):
    return lxml.etree.fromstring(v)


def dump(v):
    return lxml.etree.tostring(v)
