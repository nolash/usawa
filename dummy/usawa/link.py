import uuid
import logging

from .entry import Entry

logg = logging.getLogger('link')


class EntryLink:

    def __init__(self, ledger, refs=False):
        self.ledger = ledger
        self.idx = {}
        self.idx_ref = None
        if refs:
            self.idx_ref = {}
        self.links = {}


    def link(self, entry, link_uuid=None):
        v = self.idx.get(entry.serial)
        if v != None:
            raise FileExistsError('link {} already has entry {}'.format(v, entry))
        if link_uuid == None:
            link_uuid = entry.ref
        s = str(link_uuid)
        if self.links.get(s) == None:
            self.links[s] = []
        self.links[s].append(entry.serial)
        self.idx[entry.serial] = s
        if self.idx_ref != None:
            self.idx_ref[entry.ref] = s
        logg.debug('link {} added entry {}'.format(link_uuid, entry))

    
    def link_to(self, anchor, entry):
        if not isinstance(anchor, Entry):
            anchor = Entry.empty(serial=anchor.serial)
        v = self.get(anchor) 
        if v == None:
            v = anchor.ref
            if v == None:
                v = str(uuid.uuid4())
            self.link(anchor, link_uuid=v)
        self.link(entry, link_uuid=v)
        return v


    def get_for(self, entry):
        v = self.get(entry)
        if v == None:
            return None
        r = []
        logg.debug('link {} found for entry {}'.format(v, entry))
        for v in self.links[v]:
            if v == entry.serial:
                continue
            r.append(v)
        return r


    def get(self, entry):
        v = self.idx.get(entry.serial)
        if v != None:
            return v
        if self.idx_ref == None:
            return None
        return self.idx_ref.get(entry.ref)
