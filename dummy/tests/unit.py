import unittest

from usawa import UnitIndex


class TestUnit(unittest.TestCase):
    
    def setUp(self):
        self.uidx_default = UnitIndex('FOO')
        self.uidx_three = UnitIndex('FOO', precision=3)
        self.uidx_none = UnitIndex('FOO', precision=0)
        self.uidx_default.add('BAR', precision=4)


    def test_tostring(self):
        v = self.uidx_default.to_floatstring('FOO', 12345)
        self.assertEqual(v, '123.45')
        v = self.uidx_three.to_floatstring('FOO', 12345)
        self.assertEqual(v, '12.345')
        v = self.uidx_three.to_floatstring('FOO', 123)
        self.assertEqual(v, '0.123')
        v = self.uidx_three.to_floatstring('FOO', 1)
        self.assertEqual(v, '0.001')
        v = self.uidx_none.to_floatstring('FOO', 12345)
        self.assertEqual(v, '12345')
        v = self.uidx_none.to_floatstring('FOO', 123)
        self.assertEqual(v, '123')
        v = self.uidx_default.to_floatstring('BAR', 12345)
        self.assertEqual(v, '1.2345')


    def test_fromstring(self):
        v = self.uidx_default.from_floatstring('FOO', '123.45')
        self.assertEqual(v, 12345)
        v = self.uidx_three.from_floatstring('FOO', '12.345')
        self.assertEqual(v, 12345)
        v = self.uidx_three.from_floatstring('FOO', '0.123')
        self.assertEqual(v, 123)
        v = self.uidx_three.from_floatstring('FOO', '0.001')
        self.assertEqual(v, 1)
        v = self.uidx_none.from_floatstring('FOO', '12345')
        self.assertEqual(v, 12345)
        v = self.uidx_none.from_floatstring('FOO', '123')
        self.assertEqual(v, 123)
        v = self.uidx_default.from_floatstring('BAR', '1.2345')
        self.assertEqual(v, 12345)


if __name__ == '__main__':
    unittest.main()
