import logging
import socket

logg = logging.getLogger('handler')


class Handler:

    def __init__(self):
        self.cmd = None
        self.buf = b''
        self.c = 0
        self.l = 0
        self.state = 0


    def scan(self, v):
        self.buf = v
        if len(v) == 0:
            return -1
        if self.cmd == None:
            r = self.handle_cmd()
            if r > 0:
                return r
        if self.handle_len() > 0:
            return False
        if self.handle_collect() > 0:
            return False
        if self.cmd == 0:
            return self.handle_getlastserial()
        raise ValueError()


    def handle_cmd(self):
        self.cmd = self.buf[0]
        self.c = 1
        self.l = -1
        self.state = 1
        return self.handle_len()


    def __remainder(self):
        v = self.buf[self.c:]
        return (len(v), v,)


    def handle_len(self):
        (l, v) = self.__remainder()
        if l == 0:
            return 0
        if l < 3:
            return 3 - l
        self.l = int.from_bytes(v, byteorder='big')
        self.c += 3
        return 0


    def handle_collect(self):
        (l, v) = self.__remainder()
        self.c += l
        c = self.c - 3
        if c >= l:
            self.r = True
            self.c = l + 3
            c = l
            logg.debug('have cmd {} len {} arg {}'.format(self.cmd, self.l, self.buf[3:self.c].hex()))
        return l - c


    def handle_getlastserial(self):
        logg.debug('would get last serial')
        self.state = 0
        return 0


class SocketServer:
    
    def __init__(self, store):
        self.scks = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.store = store


    def start(self):
        scks.bind(('', 32327,))
        scks.listen(LISTEN_COUNT)
        while True:
            logg.debug('waiting for connection')
            (sckc, address) = scks.accept()
            logg.info('connect: {}'.format(address))
            #th = threading.Thread(target=self.receive, args=(sckc, address))
            #th.start()
            self.receive(sckc, address)
           

    def receive(self, sckc, address):
        c = 0
        data = bytearray()
        handler = Handler()
        while True:
            b = sckc.recv(READ_SIZE)
            if len(b) == 0:
                logg.info('connection broken: {}'.format(address))
                break
            for v in b:
                if v == 0x0a:
                    logg.debug('command boundary reached')
                    parse(bytes(data))
                data.append(v)
            logg.debug('read {}: {}'.format(len(b), b.hex()))



