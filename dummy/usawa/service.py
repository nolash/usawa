import logging
import socket

from whee import Interface
from usawa.store import LedgerStore
from usawa.error import SocketError

logg = logging.getLogger('handler')

READ_SIZE = 2048
LISTEN_COUNT = 5


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
            return -1
        if self.handle_collect() > 0:
            return -1
        return self.handle()


    def handle_cmd(self):
        self.cmd = self.buf[0]
        self.c = 1
        self.l = -1
        self.state = 1
        self.r = None
        self.v = None
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
        return l - c


    def handle(self):
        self.state = 3
        fn = self.h.get(self.cmd)
        if fn == None:
            raise ValueError()
        logg.debug('handling cmd {} arg 0x{} rest buffer 0x{}'.format(self.cmd, self.r.hex(), self.buf.hex()))
        r = fn(self.r)
        self.v = b'\x00'
        l = len(r)
        self.v += l.to_bytes(3, byteorder='big')
        self.v += r
        return 0


    def harvest(self):
        self.state = 0
        return self.v


class SocketServer:

    def __init__(self, db, ledger, acl=None):
        self.store = LedgerStore(db, ledger)
        self.acl = acl
        self.scks = None
        self.running = True


    def stop(self):
        if self.scks != None:
            self.scks.shutdown(socket.SHUT_RD)
            self.scks.close()
            self.scks = None
        self.running = False


    def start(self):
        self.scks.listen(LISTEN_COUNT)
        while self.running:
            logg.debug('waiting for connection')
            sckc = None
            address = None
            if self.scks == None:
                logg.warning('Socket gone. Bailing.')
                break
            try:
                (sckc, address) = self.scks.accept()
            except TimeoutError:
                logg.debug('timeout')
                continue
            except OSError:
                logg.warning('Socket accept aborted. Bailing.')
                break
            if sckc != None:
                logg.info('connect: {}'.format(address))
                #th = threading.Thread(target=self.receive, args=(sckc, address))
                #th.start()
                try:
                    self.receive(sckc, address)
                except ConnectionResetError:
                    logg.warning('connection reset')
                sckc.close()
                break
        

    def put(self, b):
        l = int.from_bytes(b[:3], byteorder='big')
        k = b[3:l+3]
        b = b[l+3:]
        l = int.from_bytes(b[:3], byteorder='big')
        v = b[3:l+3]
        b = b[l+3:]
        l = len(b)
        logg.debug('put parse k {} v {}'.format(k.hex(), v.hex()))
        if l > 0:
            logg.warning(str(l) + 'bytes excess put data')
        self.store.put(k, v)
        return b'\x00'


    def receive(self, sckc, address):
        c = 0
        data = bytearray()
        handler = Handler()
        handler.register(0, self.store.get)
        handler.register(1, self.put)
        while True:
            r = -1
            b = sckc.recv(READ_SIZE)
            if len(b) == 0:
                logg.info('connection broken: {}'.format(address))
                break
            try:
                r = handler.scan(b)
            except Exception as e:
                logg.warning('socket cmd fail: ' + str(type(e)))
            if r == -1:
                sckc.sendall(b'\x02')
                break
            v = handler.harvest()
            logg.debug('harvest {}'.format(v.hex()))
            sckc.sendall(v)


class UnixServer(SocketServer):

    timeout = 1

    def __init__(self, db, ledger, acl=None, path='./usawa.socket'):
        super(UnixServer, self).__init__(db, ledger, acl=acl)
        self.scks = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.scks.bind(path)
        self.scks.settimeout(UnixServer.timeout)


class TCPServer(SocketServer):
    
    timeout = 1

    def __init__(self, db, ledger, acl=None, host='', port=32327):
        super(TCPServer, self).__init__(db, ledger, acl=acl)
        self.scks = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.scks.bind((host, port,))
        self.scks.settimeout(UnixServer.timeout)



class SocketClient(Interface):

    def __init__(self):
        self.sck = None


    def close(self):
        logg.debug('request client close')
        if self.sck != None:
            self.sck.shutdown(socket.SHUT_RDWR)
            self.sck.close()

    
    """

    :todo: optimize length for key and value
    """
    def put(self, k, v):
        b = b'\x01'
        l = len(k) + len(v) + 6 # length of key and value, and serialized lengths of both (3+3)
        b += l.to_bytes(3, byteorder='big')
        l = len(k)
        b += l.to_bytes(3, byteorder='big')
        b += k
        l = len(v)
        b += l.to_bytes(3, byteorder='big')
        b += v
        self.sck.sendall(b)
        r = self.sck.recv(4)
        if r[:1] != b'\x00':
            logg.error('error return value {}'.format(r.hex()))
            raise SocketError()
        l = int.from_bytes(r[1:], byteorder='big')
        logg.debug('recv data len {} {}'.format(l, r))

        c = l
        b = b''
        while c > 0:
            r = self.sck.recv(c)
            logg.debug('recv {} {}'.format(len(r), c, l))
            if len(r) == 0:
                break
            c -= len(r)
            b += r


    def get(self, k):
        b = b'\x00'
        l = len(k)
        b += l.to_bytes(3, byteorder='big')
        b += k
        self.sck.sendall(b)
        r = self.sck.recv(4)
        if r[:1] != b'\x00':
            raise SocketError()
        l = int.from_bytes(r[1:], byteorder='big')
        logg.debug('recv data len {} {}'.format(l, r))

        c = l
        b = b''
        while c > 0:
            r = self.sck.recv(c)
            logg.debug('recv {} {}'.format(len(r), c, l))
            if len(r) == 0:
                break
            c -= len(r)
            b += r

        logg.debug('get recv data {} {}'.format(len(b), b))
        return b


class UnixClient(SocketClient):

    def __init__(self, path='./usawa.socket'):
        super(UnixClient, self).__init__()
        self.sck = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sck.connect(path)



class TCPClient:

    def __init__(self, host, port=32327):
        self.scks = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((host, port,))
