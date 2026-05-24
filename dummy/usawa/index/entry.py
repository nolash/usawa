import lxml.etree

from usawa.xml import nsmap
from usawa import Entry


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
        tree = lxml.etree.Element('index', nsmap=nsmap())
        i = 0
        while True:
            i += 1
            try:
                v = self.get_digest(i)
            except KeyError:
                break
            o = lxml.etree.Element('entry')
            o.text = v.hex()
            o.set('serial', str(i))
            if self.m & 1 > 0:
                v = self.get_ref(i)
                o.set('ref', v)
            tree.append(o)
        return tree


    @staticmethod
    def from_tree(tree):
        have_refs = False
        idx = EntryIndex(ref=True, digest=True)
        for v in tree.findall('entry'):
            ref = v.get('ref')
            if ref != None:
                have_refs = True
            digest = v.text
            digest = bytes.fromhex(digest)
            serial = int(v.get('serial'))
            o = Entry.empty(serial=serial, ref=ref)
            idx.register(o, digest=digest)
        return idx
