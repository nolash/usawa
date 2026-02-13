import hashlib
import mimetypes
import logging
import os

import magic

logg = logging.getLogger('asset')

BLOCKSIZE = 512

magic = magic.Magic(flags=magic.MAGIC_MIME_TYPE)

def parse_path(path):
    s = os.path.basename(path)
    v = s.rsplit('.', maxsplit=1)
    slug = v[0]
    ext = None
    if len(v) == 2:
        ext = v[1]
    return (slug, ext,)

class Asset:

    def __init__(self):
        self.digest = None
        self.mime = None
        self.enc = None
        self.slug = None
        self.ext = None


    

    def get_filename(self):
        s = self.slug
        if self.ext != None:
            s += '.' + self.ext
        return s


    def get_mimestring(self):
        s = self.mime
        if self.enc != None:
            s += '; encoding=' + self.enc
        return s



    @staticmethod
    def from_file(filepath, description=None, slug=None, mimetype=None):
        o = Asset()
        h = hashlib.sha256()
        f = open(filepath, 'rb')
        b = f.read(BLOCKSIZE)
        if mimetype == None:
            v = mimetypes.guess_file_type(filepath, strict=True)
            if v != None:
                mimetype = v[0]
                o.enc = v[1]
        if mimetype == None:
            mimetype = magic.id_buffer(b)
        o.mime = mimetype
        h.update(b)
        c = BLOCKSIZE
        while True:
            b = f.read(BLOCKSIZE)
            if len(b) == 0:
                break
            h.update(b)
            c += len(b)
        f.close()
        o.digest = h.digest()

        s = mimetypes.guess_extension(o.mime, strict=True)
        if s != None:
            o.ext = s[1:] 

        (o.slug, o.ext) = parse_path(filepath)

        logg.debug('asset read {} bytes from path {} mime {}'.format(c, filepath, o.mime))

        return o


    def __str__(self):
        return 'file ̈́' + self.get_filename() + ' mime ' + self.get_mimestring() + ' digest ' + self.digest.hex()
