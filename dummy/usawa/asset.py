import hashlib
import mimetypes
import logging
import os
import uuid

import lxml.etree
import rencode
import magic

from .constant import NSPREFIX
from .xml import nsmap

logg = logging.getLogger('usawa.asset')

BLOCKSIZE = 512

magic = magic.Magic(flags=magic.MAGIC_MIME_TYPE)

"""Return a stem name and extension as a tuple from an absolute or relative path.

Stem name will always be set. Extension will be returned as None if none could be found.

Does not check whether or not the file exists.

:param path: File path.
:type path: str
:raises ValueError: Empty path value.
:return: Stem name and extension.
:rtype: Tuple
"""
def parse_path(path):
    if len(path) == 0 or path == None:
        raise ValueError('empty path')
    s = os.path.basename(path)
    v = s.rsplit('.', maxsplit=1)
    slug = v[0]
    ext = None
    if len(v) == 2:
        ext = v[1]
    return (slug, ext,)


class Asset:
    """Represents a file asset, used as attachment in usawa.Entry.

    Object is not intended to be instantiated directly. Instead one of the following static methods should be used:

    Asset.from_file() - Read from local file.
    Asset.from_io() - Read from a io.BufferedIOBase input stream.
    Asset.from_tree() - Recreate from an XML tree.
    """
    def __init__(self, digest=None):
        self.digest = digest
        self.mime = None
        self.enc = None
        self.slug = None
        self.ext = None
        self.extref = None
        self.uuid = None
        self.description = None


    """Return the preferred filename with extension for the asset.

    Must always return a value. The filename may or may not have an extension.

    :return: Filename
    :rtype: str
    """
    def get_filename(self):
        s = self.slug
        if self.ext != None:
            s += '.' + self.ext
        return s


    """Return the mime type.

    The encoding specifier will be added if it exists.

    Returns None if mime type has not been set.

    :return: Mime string
    :rtype: str
    """
    def get_mimestring(self):
        s = self.mime
        if s != None:
            if self.enc != None:
                s += ';charset=' + self.enc
        return s


    """Return the digest of the asset, in hex.

    :raises AttributeError: Digest not set
    :return: Digest hex
    :rtype: str
    """
    def get_digest(self, binary=False):
        if self.digest == None:
            raise AttributeError('')
        if binary:
            return self.digest
        return self.digest.hex()


    """Instantiate an asset object from a local file.

    File is opened and the file object is passed on to the from_io() method. 

    The filepath argument will be passed as the "src" argument to from_io().

    See from_io() for documentation on the named arguments.

    :param filepath: File path to read from.
    :type filepath: str

    :raises FileNotFoundError: File does not exist.
    :raises IsADirectoryError: Path is a directory.
    :raises PermissionError: File cannot be read.
    """
    @staticmethod
    def from_file(filepath, description=None, slug=None, mimetype=None, extref=None):
        f = open(filepath, 'rb')
        return Asset.from_io(f, filepath, closer=f.close, description=description, slug=slug, mimetype=mimetype, extref=extref)


    """Instantiate an asset object from an input stream.

    Unless explicitly set, an attempt to automatically guess the mime type of the stream. If the mime type cannot be guessed by the file extension, a filemagic buffer scan is attempted (first usawa.asset.BLOCKSIZE bytes).

    :param io: Buffered input to read from.
    :type io: io.BufferedIOBase
    :param src: Source location.
    :type src: Source location
    :param closer: Function that will be called after completed read to close the io stream.
    :type closer: io.IOBase.close
    :param description: A description of the file contents.
    :type description:  to this value.
    :param slug: Override filename with this as stem name.
    :type slug: str
    :param mimetype: Explicitly set mime type to this value.
    :type mimetype: str
    :param extref: An external reference (e.g. invoice number).
    :type extref: str
    :todo: make sure stream close on exception.
    :todo: make path uri/remote url friendly when implementing remote stream.
    :todo: document possible exceptions.
    """
    @staticmethod
    def from_io(io, src, closer=None, description=None, slug=None, mimetype=None, extref=None):
        o = Asset()
        h = hashlib.sha256()
        b = io.read(BLOCKSIZE)
        if mimetype == None:
            v = mimetypes.guess_file_type(src, strict=True)
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
        if closer != None:
            closer()
        o.digest = h.digest()

        s = mimetypes.guess_extension(o.mime, strict=True)
        if s != None:
            o.ext = s[1:] 
        (o.slug, o.ext) = parse_path(src)
        if slug != None:
            logg.info('overriding file base name {} -> {}'.format(o.slug, slug))
            o.slug = slug

        logg.debug('asset read {} bytes from path {} mime {}'.format(c, src, o.mime))

        o.uuid = str(uuid.uuid4())
        o.extref = extref
        o.description = description

        return o


    """Return canonical XML for use in signature message calculation.

    Elements in canonical XML for the asset is data that can be recreated by the actual file data.

    Although MIME type may be ambigious, it can reasonably be guessed by scanning the asset data after the fact and most likely with trial-and-error from the results of that operation.

    For custom or arcane MIME types, the data needed to recreate the MIME type has to be retained outside the application.
    """
    def canon(self):
        tree = lxml.etree.Element(NSPREFIX + 'attachment', nsmap=nsmap())
        if self.mime != None:
            tree.set('mime', self.get_mimestring())

        o = lxml.etree.SubElement(tree, 'digest')
        o.set('algo', 'sha256')
        o.text = self.digest.hex()
        tree.append(o)

        return tree


    """Generate and return an XML representation of the asset.

    :param canon: Return canonical results to use in signature material.
    :type canon: boolean
    :returns: XML tree representing the asset.
    :rtype: lxml.etree.Element
    :todo: implement sigs
    """
    def to_tree(self, canon=False):
        tree = self.canon() 
        if canon:
            return tree

        if self.uuid != None:
            tree.set('uuid', self.uuid)

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


    """Create object from an asset part defined as an XML tree.

    The XML expected is an ledger/entry[]/attachment[] element (in schema defined as the Attachment complexType)

    :param tree: The asset as XML tree.
    :type tree: lxml.etree.ElementTree
    :return: Asset part
    :rtype: lxml.etree.Element
    :todo: add to docs cannot directly import from tree generated from to_tree, must go way by string export
    :todo: implement sigs
    """
    @staticmethod
    def from_tree(tree):
        o = Asset()
        o.uuid = tree.get('uuid')
        o.mime = tree.get('mime')
        v = tree.find('digest', namespaces=nsmap()).text
        o.digest = bytes.fromhex(v)

        v = tree.find('extref', namespaces=nsmap())
        if v != None:
            o.extref = v.text

        v = tree.find('filename', namespaces=nsmap())
        if v != None:
            v = parse_path(v.text)
            o.slug = v[0]
            o.ext = v[1]

        v = tree.find('description', namespaces=nsmap())
        if v != None:
            o.description = v.text

        logg.warning('asset sigs not yet implemented')
        for v in tree.findall('sig', namespaces=nsmap()):
            logg.debug('skipping sig from ' . v.get('keyid'))

        return o


    """Generate the simple data structure used for rencode serialization.

    :returns: data structure
    :rtype: list
    """
    def to_list(self):
        d = [
                self.mime,
                self.uuid,
                self.extref,
                self.slug,
                self.ext,
                self.description,
                ]
        return d


    """Generate the serialization format used to calculate the digest for the asset.

    :returns: String representation of the entry, in rencode format.
    :rtype: str
    """
    def serialize(self):
        b = self.to_list()
        return rencode.dumps(b)


    """Create an entry object from serialized data.

    :param data: rencoded entry object, as produced by the serialize() method.
    :type data: str
    :returns: Entry object.
    :rtype: usawa.Entry
    """
    @staticmethod
    def deserialize(data, digest):
        o = Asset()
        v = rencode.loads(data)
        i = 0
        for k in ['mime', 'uuid', 'extref', 'slug', 'ext', 'description']:
            if v[i] != None:
                setattr(o, k, v[i].decode('utf-8'))
            i += 1
        if isinstance(digest, str):
            digest = bytes.fromhex(digest)
        o.digest = digest
        return o


    def __str__(self):
        return 'file ̈́' + self.get_filename() + ' mime ' + self.get_mimestring() + ' digest ' + self.digest.hex()
