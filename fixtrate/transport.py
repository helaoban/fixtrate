import asyncio
import logging

logger = logging.getLogger(__name__)


__all__ = ("Transport", "TCPTransport")


class Transport:

    async def read(self) -> bytes:
        raise NotImplementedError

    async def write(self, msg) -> None:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError


class TCPTransport(Transport):

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ) -> None:
        self.reader = reader
        self.writer = writer

    async def read(self) -> bytes:
        data = await self.reader.read(4096)
        if data == b'':
            raise ConnectionAbortedError(
                'Peer closed the connection!')
        return data

    async def write(self, msg) -> None:
        try:
            self.writer.write(msg)
        except RuntimeError as error:
            raise ConnectionError(str(error)) from error
        await self.writer.drain()

    async def close(self) -> None:
        self.writer.close()
        await self.writer.wait_closed()

    @classmethod
    async def connect(
        cls,
        host: str,
        port: int
    ) -> "TCPTransport":
        reader, writer = await asyncio.open_connection(
            host=host, port=port)
        return cls(reader, writer)
