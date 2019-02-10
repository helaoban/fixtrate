import asyncio
import logging
from urllib.parse import urlparse

from .base import Transport

logger = logging.getLogger(__name__)


class TCPTransport(Transport):

    def __init__(self):
        self._reader = None
        self._writer = None
        self._tries = 5
        self._retry_wait = 5
        self._closing = False
        self._closed = False

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

    async def connect(self, url):
        url = urlparse(url)

        tried = 1
        while tried <= self._tries:
            try:
                reader, writer = await asyncio.open_connection(
                    host=url.hostname,
                    port=url.port,
                )
            except OSError as error:
                logger.error(error)
                logger.info('Connection failed, retrying in {} seconds...'
                            ''.format(self._retry_wait))
                tried += 1
                await asyncio.sleep(self._retry_wait)
                continue

            self._reader, self._writer = reader, writer
            return

        logger.info('Connection tries ({}) exhausted'.format(self._tries))
        raise ConnectionError

    async def close(self):
        if not self.is_closing():
            self._writer.close()
            self._closed = True

    async def is_closing(self):
        return self._closed
