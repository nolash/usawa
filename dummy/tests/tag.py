import unittest
import logging

from usawa.tag import Tags

logging.basicConfig(level=logging.DEBUG)


class TestTag(unittest.TestCase):

    def test_tags_serialize(self):
        o = Tags()
        o.add('foo')
        o.add('bar', description='baz')
        v = o.serialize()
        o = Tags.deserialize(v)
        self.assertEqual('foo, bar', str(o))


if __name__ == '__main__':
    unittest.main()
