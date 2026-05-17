import uuid


class EntryLink:

    def __init__(self, ledger):
        self.ledger = ledger
        self.idx = {}
        self.links = {}


    def link(self, entry, link_uuid=None):
        v = self.idx.get(entry.serial)
        if v != None:
            raise FileExistsError('link {} already has entry {}'.format(v, entry))
        if link_uuid == None:
            link_uuid = uuid.uuid4()
        s = str(link_uuid)
        if self.links.get(s) == None:
            self.links[s] = []
        self.links[s].append(entry.serial)
        self.idx[entry.serial] = s
