import logging

import lxml.etree

from usawa import Entry
from usawa.xml import nsmap, XML_FORMAT_VERSION

logg = logging.getLogger('usawa.entryindex')


class EntryIndex:

    def __init__(self, ref=True, digest=False):
        self.idx = {}
        self.idx_r = {}
        self.idx_z = {}
        self.idx_zr = {}
        self.m = 0
        if ref:
            self.m |= 1
        if digest:
            self.m |= 2
        if self.m == 0:
            raise AttributeError('nonsense index without anything to index')


    def register(self, entry, digest=None):
        if self.m & 1 > 0:
            if entry.ref == None:
                raise AttrubuteError('ref missing')
            self.idx[entry.serial] = entry.ref
            self.idx_r[entry.ref] = entry.serial
        if self.m & 2 > 0:
            if digest == None:
                digest = entry.sum()[0]
            self.idx_z[entry.serial] = digest
            self.idx_zr[digest] = entry.serial


    def get_ref(self, entry):
        if self.m & 1 == 0:
            raise AttributeError('not a ref index')
        v = entry
        if isinstance(v, Entry):
            v = entry.serial
        return self.idx[v]


    def get_digest(self, entry):
        if self.m & 2 == 0:
            raise AttributeError('not a digest index')
        v = entry
        if isinstance(v, Entry):
            v = entry.serial
        return self.idx_z[v]


    def to_tree(self):
        tree = lxml.etree.XML('<ledger xmlns="http://usawa.defalsify.org/" version="{}"></ledger>'.format(XML_FORMAT_VERSION))
        i = 0
        while True:
            i += 1
            try:
                v = self.get_digest(i)
            except KeyError:
                break
            entry = lxml.etree.Element('entry', nsmap=nsmap())
            entry.set('digest', v.hex())
            o = lxml.etree.SubElement(entry, 'serial')
            o.text = str(i)
            if self.m & 1 > 0:
                v = self.get_ref(i)
                o = lxml.etree.SubElement(entry, 'ref')
                o.text = str(v)
            tree.append(entry)
        return tree


    @staticmethod
    def from_tree(tree):
        have_refs = False
        idx = EntryIndex(ref=True, digest=True)
        for v in tree.findall('entry', namespaces=nsmap()):
            digest = v.get('digest')
            digest = bytes.fromhex(digest)
            o = v.find('serial', namespaces=nsmap())
            serial = int(o.text)
            o = v.find('ref', namespaces=nsmap())
            ref = None
            if o != None:
                have_refs = True
                ref = o.text
            entry = Entry.empty(serial=serial, ref=ref)
            idx.register(entry, digest=digest)
        return idx


    def to_string(self):
        tree = self.to_tree()
        return lxml.etree.tostring(tree, encoding='ascii', method="html")


    @staticmethod
    def from_string(s):
        tree = lxml.etree.fromstring(s)
        return EntryIndex.from_tree(tree)
