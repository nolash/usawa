import logging
import socket

from usawa.store import LedgerStore

logg = logging.getLogger('handler')


class Handler:

    cmd_len = 1
    len_len = 3

    def __init__(self):
        self.cmd = None
        self.buf = b''
        self.c = 0
        self.l = 0
        self.r = None
        self.state = 0
        self.h = {}


    def register(self, k, fn):
        self.h[k] = fn


    def scan(self, v):
        self.buf += v
        if self.state == 0:
            r = self.handle_cmd()
            if r > 0:
                return r
        if self.handle_len() > 0:
            return False
        if self.handle_collect() > 0:
            return False
        return self.handle()


    def handle_cmd(self):
        self.cmd = self.buf[0]
        self.c = 1
        self.l = -1
        self.state = 1
        self.r = None
        return self.handle_len()


    def __remainder(self):
        v = self.buf[self.c:]
        return (len(v), v,)


    def handle_len(self):
        if self.state != 1:
            return -1
        (l, v) = self.__remainder()
        if l == 0:
            return 0
        if l < 3:
            return 3 - l
        v = self.buf[1:4]
        self.l = int.from_bytes(v, byteorder='big')
        self.c += 3
        self.state = 2
        logg.debug('cmd {} has len {}'.format(self.cmd, self.l))
        return 0


    def handle_collect(self):
        if self.state != 2:
            return -1
        (l, v) = self.__remainder()
        self.c += l
        c = self.c - 4
        if c >= l:
            c = self.l + 4
            self.state = 3
            self.r = self.buf[4:c]
            self.buf = self.buf[c:]
            self.c = 0
            c = l
            logg.debug('have cmd {} len {} arg {}'.format(self.cmd, self.l, self.buf[3:self.c].hex()))
        return l - c


    def handle(self):
        self.state = 0
        fn = self.h.get(self.cmd)
        if fn == None:
            raise ValueError()
        logg.debug('handling cmd {} arg 0x{} rest buffer 0x{}'.format(self.cmd, self.r.hex(), self.buf.hex()))
        return fn(self.r)


class SocketServer:
    
    def __init__(self, db, ledger, acl=None):
        self.scks = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.store = LedgerStore(db, ledger)
        self.acl = acl


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
