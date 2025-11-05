import sys
import logging
import datetime

from lxml import etree

from svcontas import load, get_units, init_ledger

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()


if __name__ == '__main__':
    fp = 'running.xml'
    try:
        fp = sys.argv[1]
    except IndexError:
        pass
    root = load(fp) 
    un = get_units(root)
    st = init_ledger(root, un)
    st.apply_tree(root)
    print(st)
