import unittest
import logging

from usawa.base import UsawaElement

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()


class TestElement(unittest.TestCase):

    def test_element_serialize(self):
        o = UsawaElement()
        o.add_tag('foo')
        o.add_tag('bar')
        o.add_tag('baz')
        o.add_pair('inky', 'pinky')
        o.add_pair('blinky', 'clyde')

        v = o.serialize()
        o = UsawaElement()
        o.deserialize(v)


if __name__ == '__main__':
    unittest.main()
