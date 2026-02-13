import hashlib
import mimetypes
import logging
import os
import uuid

import lxml.etree
import magic

from .xml import nsmap

logg = logging.getLogger('usawa.asset')

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
        self.localref = None
        self.extref = None
        self.uuid = None
        self.description = None


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
    def from_file(filepath, description=None, slug=None, mimetype=None, localref=None, extref=None):
        f = open(filepath, 'rb')
        return Asset.from_io(f, filepath, f.close, description=description, slug=slug, mimetype=mimetype, localref=localref, extref=extref)


    """
    :todo: make sure stream close on exception
    """
    @staticmethod
    def from_io(io, path, closer, description=None, slug=None, mimetype=None, localref=None, extref=None):
        o = Asset()
        h = hashlib.sha256()
        b = io.read(BLOCKSIZE)
        if mimetype == None:
            v = mimetypes.guess_file_type(path, strict=True)
            if v != None:
                mimetype = v[0]
                o.enc = v[1]
        if mimetype == None:
            mimetype = magic.id_buffer(b)
        o.mime = mimetype
        h.update(b)
        c = BLOCKSIZE
        while True:
            b = io.read(BLOCKSIZE)
            if len(b) == 0:
                break
            h.update(b)
            c += len(b)
        closer()
        o.digest = h.digest()

        s = mimetypes.guess_extension(o.mime, strict=True)
        if s != None:
            o.ext = s[1:] 
        (o.slug, o.ext) = parse_path(path)
        if slug != None:
            logg.info('overriding file base name {} -> {}'.format(o.slug, slug))
            o.slug = slug

        logg.debug('asset read {} bytes from path {} mime {}'.format(c, path, o.mime))

        o.uuid = str(uuid.uuid4())
        if localref == None:
            localref = o.uuid
        o.localref = localref
        o.extref = extref
        o.description = description

        return o


    def to_tree(self):
        tree = lxml.etree.Element('attachment', nsmap=nsmap())
        tree.set('mime', self.get_mimestring())
        tree.set('uuid', self.uuid)

        o = lxml.etree.SubElement(tree, 'digest')
        o.text = self.digest.hex()
        tree.append(o)

        o = lxml.etree.SubElement(tree, 'lookup')
        o.text = '.'
        o.set('method', 'local')
        tree.append(o)

        o = lxml.etree.SubElement(tree, 'ref')
        o.text = self.localref
        tree.append(o)

        if self.extref != None:
            o = lxml.etree.SubElement(tree, 'extref')
            o.text = self.extref
            tree.append(o)

        o = lxml.etree.SubElement(tree, 'filename')
        o.text = self.get_filename()
        tree.append(o)

        if self.description != None:
            o = lxml.etree.SubElement(tree, 'description')
            o.text = self.description
            tree.append(o)

        return tree
 

    def __str__(self):
        return 'file ̈́' + self.get_filename() + ' mime ' + self.get_mimestring() + ' digest ' + self.digest.hex()
