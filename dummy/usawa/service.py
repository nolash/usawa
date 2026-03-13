import logging
import socket
import os
import threading

from whee import Interface
from usawa.store import LedgerStore
from usawa.error import SocketError

logg = logging.getLogger('handler')

READ_SIZE = 2048
LISTEN_COUNT = 5
#CMD_LEN = 1
#LEN_LEN = 3

class Handler:
    """Buffers and parses instruction data from a client, and executes code corresponding to the command given.

    The instance may be reused.
    """
    def __init__(self):
        self.cmd = None
        self.buf = b''
        self.c = 0
        self.l = 0
        self.r = None
        self.state = 0
        self.h = {}


    """Register execution code for a command byte.
    """
    def register(self, k, fn):
        self.h[k] = fn


    """Single processing pass on buffer to read and execute an instruction. 

    The process consists of four parts:

    1. Initialize the handler and read the command byte.
    2. Read the content length
    3. Read the contents
    4. Execute code on the contents as specified by the command byte.

    Once an instruction is successfully executed, the consecutive call will start over from the first step.

    :raises BufferError: Initialization attempted on an empty buffer.
    :raises ValueError: Code for command byte does not exist
    :return: -1 if further parsing is required, 0 for successful execution, any other positive value indicates an error.
    :rtype: int
    """
    def scan(self, v):
        if self.state == 4:
            self.state = 0
        self.buf += v
        if self.state == 0:
            self.handle_cmd()
        r = self.handle_len()
        if r > 0:
            return -1
        r = self.handle_collect()
        if r > 0:
            return -1
        return self.handle_exec()


    """Initialize the handler for parsing a new instruction.

    :raises BufferError: If buffer is empty.
    """
    def handle_cmd(self):
        if len(self.buf) == 0:
            raise BufferError('empty buffer')
        self.cmd = self.buf[0]
        self.c = 1
        self.l = -1
        self.state = 1
        self.r = None
        self.v = None


    def __remainder(self):
        v = self.buf[self.c:]
        return (len(v), v,)


    """Parse the length of the command contents.
    
    If it returns 0, there are no bytes remaining to read and the contents can be parsed with the handle_collect() method.

    If it returns a positive value, handle_collect() should be called again once more data is available to complete the parsing.

    :return: 0 if complete, -1 if not in correct state, or bytes remaining to read.
    :rtype: int
    """
    def handle_len(self):
        if self.state == 0:
            return -1
        if self.state != 1:
            return 0
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


    """Read the instruction up to the full indicated length.

    If it returns 0, there are no bytes remaining to read and the code can be executed with the handle() method.

    If it returns a positive value, handle_collect() should be called again once more data is available to complete the parsing.

    :return: 0 if complete, -1 if not in correct state, or bytes remaining to read.
    :rtype: int
    """
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


    """Execute the code corresponding to the command for a fully parsed instruction.

    The code for the command byte has to have been registered using the register() method.

    After successful execution, the result of the operation can be read using the harvest() method.

    :raises ValueError: No code registered for the command
    :return: 0 on successful execution, any other value indicates error.
    :rtype: int
    """
    def handle_exec(self):
        self.state = 3
        fn = self.h.get(self.cmd)
        if fn == None:
            self.state = 4
            raise ValueError()
        logg.debug('handling cmd {} arg 0x{} rest buffer 0x{}'.format(self.cmd, self.r.hex(), self.buf.hex()))
        r = fn(self.r)
        if r == None:
            self.state = 5
            return 1
        self.v = b'\x00'
        l = len(r)
        self.v += l.to_bytes(3, byteorder='big')
        self.v += r
        return 0


    """Retrieve the completed result of the operation
    """
    def harvest(self):
        if self.state < 3:
            raise AttributeError('processing not complete')
        if self.state == 4:
            raise AttributeError('processing failed unexpectedly, no data available.')
        if self.state == 5:
            raise ValueError('no data')
        self.state = 0
        return self.v


class SocketServer:
    """Store agnostic middleware for remote connections.

    Each instruction to the server is prefixed by a single-byte command identifier and a 3-byte big-endian length value specifying the total length of the contents to be sent to the backend.

    The get command has the byte value 0x00. The content is the literal key to retrieve from the store (e.g. the value of usawa.store.pfx_entry())

    The put command has the byte value 0x01. The content is a key and value pair, each prefixed by their own 3-byte big-endian length value, specifying the total length of the key and value respectively. 

    The server returns a result code and optionally a payload. The return value consists of a single byte result code, and a 3-byte big-endian length value specifying the total length of the return value. A length value of 0x000000 means the command returns and empty payload. A return value of 0x00 indicates success, any other value indicates failure.

    The server wraps usawa.Handler, which handles parsing and buffering the client submissions, and sending to the right handler - put or get.

    :param db: The underlying store to provide remote access to.
    :type db: whee.Interface
    :param ledger: The ledger the server operates on.
    :type ledger: usawa.Ledger
    :param acl: ACL to use for verifications.
    :type acl: usawa.ACL
    :todo: Ensure ACL overrides existing ACL in ledger.
    """
    def __init__(self, db, ledger, acl=None):
        self.store = LedgerStore(db, ledger)
        self.acl = acl
        self.scks = None
        self.running = True


    """Shut down the socket and execution loop.

    This function is noop if called more than once.
    """
    def stop(self):
        if self.scks != None:
            self.scks.shutdown(socket.SHUT_RD)
            self.scks.close()
            self.scks = None
        self.running = False


    """Start server listening loop.

    This method does not return until the server is stopped.
    """
    def start(self):
        logg.info('starting server: ' + str(self))
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
                th = threading.Thread(target=self.receive, args=(sckc, address))
                th.start()


    """Implements whee.Interface

    Executes the underlying db get, but catches file not found exception
    """
    def get(self, k):
        r = None
        try:
            r = self.store.get(k)
        except FileNotFoundError:
            logg.debug('key not found: {}'.format(k.hex()))
            pass
        return r
   

    """Implements whee.Interface

    Splits the content of the command to its individual key and value parts.
    """
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


    """Handles a client session.

    Does not return 

    
    """
    def receive(self, sckc, address):
        c = 0
        data = bytearray()
        handler = Handler()
        #handler.register(0, self.store.get)
        handler.register(0, self.get)
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
                logg.warning('socket cmd fail {}: {}' + str(type(e.__class__)), e)
            if r == -1:
                sckc.sendall(b'\x02')
                break
            try:
                v = handler.harvest()
            except ValueError:
                v = b'\x01'
            logg.debug('harvest {}'.format(v.hex()))
            sckc.sendall(v)
        sckc.close()


    def __str__(self):
        return str(self.__class__.__name__) + '@' + self.path



class UnixServer(SocketServer):

    timeout = 1 # Timeout for socket listen loop.

    """Implements usawa.service.SocketServer 

    See SocketServer for definintion of remaining parameters.

    :param path: Path to socket file to bind to.
    :type host: str
    """

    def __init__(self, db, ledger, acl=None, path='./usawa.socket'):
        super(UnixServer, self).__init__(db, ledger, acl=acl)
        self.path = os.path.realpath(path)
        self.scks = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.scks.bind(self.path)
        self.scks.settimeout(UnixServer.timeout)


    def __del__(self):
        logg.debug("removing socket file " + self.path)
        os.remove(self.path)



class TCPServer(SocketServer):

    timeout = 1 # Timeout for socket listen loop.

    """Implements usawa.service.SocketServer 

    See SocketServer for definintion of remaining parameters.

    :param host: Host to IP address to bind server to.
    :type host: str
    :param port: Port to bind server to.
    :type port: int
    """
    def __init__(self, db, ledger, acl=None, host='', port=32327):
        super(TCPServer, self).__init__(db, ledger, acl=acl)
        self.scks = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.scks.bind((host, port,))
        self.scks.settimeout(UnixServer.timeout)
        self.path = host + ':' + str(port)



class SocketClient(Interface):
    """Base class for clients to usawa.service.SocketServer.

    It can be used as the implementation argument for the usawa.LedgerStore.

    The implementing class should complete the connection within the class initializer.

    :todo: Implement the remaining needed methods needed by all usawa.LedgerStore methods.
    """
    def __init__(self):
        self.sck = None

 
    def __del__(self):
        self.close()   

    """Close the underlying connection.

    Is noop if called more than once.
    """
    def close(self):
        logg.debug('request client close')
        if self.sck != None:
            self.sck.shutdown(socket.SHUT_RDWR)
            self.sck.close()


    """Implements whee.Interface.

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


    """Implements whee.Interface.
    """
    def get(self, k):
        b = b'\x00'
        l = len(k)
        b += l.to_bytes(3, byteorder='big')
        b += k
        self.sck.sendall(b)
        r = self.sck.recv(4)
        if r[:1] != b'\x00':
            if r[:1] == b'\x01':
                raise FileNotFoundError(k.hex())
            else:
                logg.debug('error get value: {}'.format(r.hex()))
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
    """Implements usawa.service.SocketClient.

    :param path: Path to socket file
    :type path: str
    """
    def __init__(self, path='./usawa.socket'):
        super(UnixClient, self).__init__()
        self.sck = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sck.connect(path)


class TCPClient:

    """Implements usawa.service.TCPClient.

    :param host: Hostname or IP address to bind server to.
    :type host: str
    :param port: Port to bind server to.
    :type port: int
    """
    def __init__(self, host, port=32327):
        self.scks = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((host, port,))
