import unittest
import logging
import tempfile
import hashlib
import shutil
import os

from usawa.resolve.fs import FSResolver
from usawa.error import VerifyError


logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

hash_of_foo = 'f7fbba6e0636f890e56fbbf3283e524c6fa3204ae298382d624741d0dc6638326e282c41be5e4254d8820772c5518a2c5a8c0c7f7eda19594a7eb539453e1ed7'
hash_of_bar = 'd82c4eb5261cb9c8aa9855edd67d1bd10482f41529858d925094d173fa662aa91ff39bc5b188615273484021dfb16fd8284cf684ccf0fc795be3aa2fc1e6c181'

class TestResolver(unittest.TestCase):
    
    def setUp(self):
        self.path = tempfile.mkdtemp()
        self.backend = FSResolver(self.path) 


    def tearDown(self):
        shutil.rmtree(self.path)


    def test_resolve_putget(self):
        h = hashlib.sha512()
        v = os.urandom(1337)
        h.update(v)
        k = h.digest()
        self.backend.put(k, v)
        r = self.backend.get(k)
        self.assertEqual(r, v)

        k_wrong = os.urandom(32)
        with self.assertRaises(ValueError):
            r = self.backend.get(k_wrong)

    
    def test_resolve_get_evil(self):
        fp = os.path.join(self.path, hash_of_foo)
        f = open(fp, 'wb')
        f.write(b'bar')
        f.close()
        with self.assertRaises(VerifyError):
            self.backend.get(hash_of_foo)


if __name__ == '__main__':
    unittest.main()
