import uuid
import logging

import rencode


logg = logging.getLogger('base')


def sanitize_key(k):
    if isinstance(k, bytes):
        k = k.decode('utf-8')
    elif not isinstance(k, str):
        raise ValueError('key must be str')
    if '=' in k:
        raise ValueError('invalid key')
    return k


class UsawaElement:

    def __init__(self, ref=None):
        if ref == None:
            self.ref = str(uuid.uuid4())
        else:
            str(uuid.UUID(ref))
            self.ref = ref
        self.kv = {}


    def get_ref(self, binary=False):
        ref = self.ref
        if binary:
            ref = uuid.UUID(ref).bytes
        return ref


    def add_tag(self, k):
        k = sanitize_key(k)
        if self.kv.get(k):
            raise KeyError("key '{}' exists".format(k))
        self.kv[k] = True
        logg.debug('add tag {} to {}'.format(k, self.ref))


    def add_pair(self, k, v):
        k = sanitize_key(k)
        if self.kv.get(k):
            raise KeyError('{} exists'.format(k))
        self.kv[k] = v
        logg.debug('add key {} to {}'.format(k, self.ref))


    def get(self, k):
        return self.kv.get(k)


    def serialize(self):
        d = []
        for k in self.kv.keys():
            d.append((k, self.kv[k],))
        return d


    def deserialize(self, data):
        self.t = []
        self.kv = {}
        try:
            o = rencode.loads(data)
        except TypeError:
            o = data
        except ValueError:
            return
        i = 0
        for i in range(len(o)):
            v = o[i][1]
            k = o[i][0]
            k = sanitize_key(k)
            if isinstance(v, bool):
                self.add_tag(k)
                continue
            if isinstance(v, bytes):
                v = v.decode('utf-8')
            self.add_pair(k, v)
