import logging
import os
import unittest

from usawa.asset import Asset

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

testdir = os.path.realpath(os.path.dirname(__file__))


class TestAsset(unittest.TestCase):
   
    def test_asset_file(self):
        fp = os.path.join(testdir, 'test.xml')
        asset = Asset.from_file(fp)
        logg.debug('asset {}'.format(asset))


if __name__ == '__main__':
    unittest.main()
