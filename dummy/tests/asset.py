import logging
import os
import unittest

import lxml.etree

from usawa.asset import Asset


logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.realpath(os.path.dirname(__file__))


class TestAsset(unittest.TestCase):
   
    def test_asset_file(self):
        fp = os.path.join(testdir, 'test.xml')
        asset = Asset.from_file(fp)
        logg.debug('asset {}'.format(asset))


    def test_asset_export(self):
        fp = os.path.join(testdir, 'test.xml')
        asset = Asset.from_file(fp, slug='foo', description='barbarbar', extref='xyzzy', localref='plugh')
        tree = asset.to_tree()
        logg.debug('asset {}'.format(lxml.etree.tostring(tree)))


if __name__ == '__main__':
    unittest.main()
