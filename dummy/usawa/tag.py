import rencode

class Tags:

    def __init__(self, store=None):
        self.store = store
        self.tags = {}


    def add(self, tag, description=None):
        self.tags[tag] = description
        if self.store != None:
            self.store.put_tag(tag, description)


    def to_list(self):
        return list(self.tags.keys())


    def serialize(self):
        v = self.to_list()
        return rencode.dumps(v)


    @staticmethod
    def deserialize(data, store=None):
        r = rencode.loads(data)
        o = Tags(store=store)
        for k in r:
            k = k.decode('utf-8')
            v = None
            if o.store != None:
                v = o.store.get_tag(k)
            o.add(k, description=v)
        return o


    def __str__(self):
        v = ', '.join(list(self.tags.keys()))
        return v
