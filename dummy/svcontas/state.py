import logging

from .constant import DEFAULTPARENT

logg = logging.getLogger('svcontas.state')


class State:

    def __init__(self):
        self.serial = 0
        self.base = DEFAULTPARENT


    def poke(self, serial, base):
        if serial > self.serial:
            logg.debug('new latest state {} {}'.format(serial, base.hex()))
            self.serial = serial
            self.base = base
        return self.serial


    def save(self):
        f = open('.state', 'wb')
        b = self.serial.to_bytes(8, byteorder='big')
        f.write(b)
        f.close()
        return self.serial


    def load(self):
        try:
            f = open('.state', 'rb')
        except FileNotFoundError:
            return self.save()
        b = f.read(8)
        f.close()
        self.serial = int.from_bytes(b, byteorder='big')
        return self.serial
