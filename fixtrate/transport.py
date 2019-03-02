import asyncio
import logging

logger = logging.getLogger(__name__)


class Transport:

    def __init__(self, options=None):
        if options is None:
            options = {}
        self.options = options

    def is_closing():
        raise NotImplementedError

    async def read(self):
        raise NotImplementedError

    async def write(self, msg):
        raise NotImplementedError

    async def connect(self, url):
        raise NotImplementedError

    async def close(self):
        raise NotImplementedError


class TCPTransport(Transport):

    def __init__(self, options=None):
        super().__init__(options)
        self.reader = None
        self.writer = None

    def is_closing(self):
        if self.writer is not None:
            return self.writer.transport.is_closing()
        return False

    async def read(self):
        data = await self.reader.read(4096)
        if data == b'':
            raise ConnectionAbortedError(
                'Peer closed the connection!')
        return data

    async def write(self, msg):
        self.writer.write(msg)
        await self.writer.drain()

    async def connect(self, host, port):
        self.reader, self.writer = await asyncio.open_connection(
            host=host, port=port)

    async def close(self):
        if self.writer is not None:
            if not self.writer.transport.is_closing():
                self.writer.close()


class TCPListenerTransport(TCPTransport):
    async def connect(self, reader, writer):
        self.reader = reader
        self.writer = writer


def make_transport(options):
    transport_cls = options['transport']
    if transport_cls is None:
        transport_cls = TCPTransport
    return transport_cls(options['transport_options'])
