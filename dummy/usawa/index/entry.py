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


    def register(self, entry):
        if self.m & 1 > 0:
            if entry.ref == None:
                raise AttrubuteError('ref missing')
            self.idx[entry.serial] = entry.ref
            self.idx_r[entry.ref] = entry.serial
        if self.m & 2 > 0:
            z = entry.sum()
            self.idx_z[entry.serial] = z
            self.idx_zr[z] = entry.serial


    def get_ref(self, entry):
        if self.m & 1 == 0:
            raise AttributeError('not a ref index')
        return self.idx[entry.serial]


    def get_digest(self, entry):
        if self.m & 1 == 0:
            raise AttributeError('not a ref index')
        return self.idx_z[entry.serial]
