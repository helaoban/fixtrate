import asyncio
import logging
from fixtrate.utils.aio import Sleeper

logger = logging.getLogger(__name__)


class Transport:

    def __init__(self, options=None):
        if options is None:
            options = {}
        self.options = options

    async def read(self):
        raise NotImplementedError

    async def write(self, msg):
        raise NotImplementedError

    async def connect(self, url):
        raise NotImplementedError

    async def close(self):
        raise NotImplementedError

    async def is_closing(self):
        raise NotImplementedError


class TCPTransport(Transport):

    def __init__(self, options=None):
        super().__init__(options)
        self._reader = None
        self._writer = None
        self._tries = 5
        self._retry_wait = 5
        self._closing = False
        self._closed = False
        self._connecting = False

        self.sleeper = Sleeper()

    async def read(self):
        try:
            data = await self._reader.read(4096)
        except ConnectionError as error:
            logger.error(error)
            await self.close()
            raise
        if data == b'':
            logger.error('Peer closed the connection!')
            await self.close()
            raise ConnectionAbortedError
        return data

    async def write(self, msg):
        self._writer.write(msg)
        try:
            await self._writer.drain()
        except ConnectionError as error:
            logger.error(error)
            await self.close()

    async def connect(self, host, port):
        if self.is_closing():
            raise RuntimeError('Transport is closed.')
        self._connecting = True
        tried = 1
        while tried <= self._tries:
            try:
                reader, writer = await asyncio.open_connection(
                    host=host,
                    port=port,
                )
            except OSError as error:
                logger.error(error)
                logger.info(
                    'Connection failed, retrying in {} seconds...'
                    ''.format(self._retry_wait))
                tried += 1
                try:
                    await self.sleeper.sleep(self._retry_wait)
                except Exception as error:
                    print(error)
                    raise
                if not self.is_closing():
                    continue
                else:
                    error = 'Transport was closed while attempting to connect'
                    raise ConnectionAbortedError(error)

            self._reader, self._writer = reader, writer
            self._connecting = False
            return

        logger.info('Connection tries ({}) exhausted'.format(self._tries))
        raise ConnectionError

    async def close(self):
        if not self.is_closing():
            self._closing = True
            if self._connecting:
                await self.sleeper.cancel_all()
            if self._writer is not None:
                self._writer.close()
            self._closing = False
            self._closed = True

    def is_closing(self):
        return self._closing or self._closed


def make_transport(options):
    transport_cls = options['transport']
    if transport_cls is None:
        transport_cls = TCPTransport
    return transport_cls(options['transport_options'])
