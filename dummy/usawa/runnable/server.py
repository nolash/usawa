import socket
import logging

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()


def parse(v):
    logg.debug('parsing {}'.format(v.hex()))

def main():
    scks = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    scks.bind(('', 32327,))
    scks.listen(1)
    while True:
        logg.debug('waiting for connection')
        (sckc, address) = scks.accept()
        logg.info('connect: {}'.format(address))
        c = 0
        data = bytearray()
        while True:
            b = sckc.recv(2048)
            if len(b) == 0:
                logg.info('connection broken: {}'.format(address))
                break
            for v in b:
                if v == 0x0a:
                    logg.debug('command boundary reached')
                    parse(bytes(data))
                data.append(v)
            logg.debug('read {}: {}'.format(len(b), b.hex()))


if __name__ == '__main__':
    main()
