import asyncio as aio
from dataclasses import dataclass
import logging
import typing as t
from copy import copy

from . import exceptions as exc
from .session import FixSession
from .parse import FixParser
from .transport import Transport, TCPTransport
from .store import create_store
from .message import FixMessage
from .fixt.types import FixTag as TAGS
from .config import FixSessionConfig


__all__ = ("FixServer", "FixServerConfig")


if t.TYPE_CHECKING:
    SessionID = t.Tuple[str, str, str, t.Optional[str]]


logger = logging.getLogger(__name__)


VALID_FIX_VERSIONS = {"FIX.4.2"}


def swap_session_id(session_id: "SessionID"):
    version, sender, target, qualifier = session_id
    return version, target, sender, qualifier


@dataclass
class FixServerConfig:
    host: str
    port: int
    store: str = "inmemory://"


class FixServer:
    def __init__(
        self,
        config: FixServerConfig,
        client_configs: t.Iterable[FixSessionConfig],
    ) -> None:
        self.config = config
        self.sessions: "t.Dict[SessionID, FixSession]" = {}
        self.server: t.Optional[aio.events.AbstractServer] = None
        self._session_queue: aio.Queue = aio.Queue()
        self.client_configs: "t.Dict[SessionID, FixSessionConfig]" = {}
        for client_config in client_configs:
            session_id = (
                client_config.version,
                client_config.sender,
                client_config.target,
                client_config.qualifier,
            )
            self.client_configs[session_id] = client_config

    def __aiter__(self) -> t.AsyncIterator[FixSession]:
        return self

    async def __anext__(self) -> FixSession:
        try:
            return await self.get_session()
        except exc.BindClosedError:
            raise StopAsyncIteration

    async def get_session(self) -> FixSession:
        session = await self._session_queue.get()
        if session is None:
            raise exc.BindClosedError
        return session

    def authenticate(self, msg: FixMessage) -> FixSessionConfig:
        # TODO need to check that the session target
        # matches the "sender" that the server was bound to
        begin_string = msg.get_or_raise(TAGS.BeginString)
        sender = msg.get_or_raise(TAGS.SenderCompID)
        target = msg.get_or_raise(TAGS.TargetCompID)

        if begin_string not in VALID_FIX_VERSIONS:
            err_msg = (
                f"{begin_string} in an invalid"
                "or unsupported FIX version"
            )
            raise exc.FIXAuthenticationError(err_msg)

        # TODO we don't actually support a qualifier string
        # so we should ask why we ask for one in the config
        # in the first place.
        session_id = (begin_string, sender, target, "")

        try:
            existing = self.sessions[session_id]
        except KeyError:
            pass
        else:
            if existing.closed:
                self.sessions.pop(session_id)
            else:
                err_msg = "A connection is already bound to this session."
                raise exc.FIXAuthenticationError(err_msg)

        try:
            client_config = self.client_configs[session_id]
        except KeyError as error:
            raise exc.FIXAuthenticationError(
                "Invalid FIX session parameters"
            ) from error

        config = copy(client_config)
        config.sender = client_config.target
        config.target = client_config.sender
        return config

    async def read(self, transport: Transport) -> bytes:
        try:
            # TODO How long to wait for Logon msg after TCP
            # connection made?
            data = await aio.wait_for(transport.read(), timeout=1)
        except aio.TimeoutError as error:
            raise exc.UnresponsiveClientError from error
        return data

    async def create_session(self, transport: Transport) -> FixSession:
        tmp_parser = FixParser()
        buf = b""
        while True:
            first_msg = tmp_parser.get_message()
            if first_msg:
                break
            data = await self.read(transport)
            tmp_parser.append_buffer(data)
            buf = buf + data

        config = self.authenticate(first_msg)
        store = await create_store(config, self.config.store)
        session = FixSession(
            config=config,
            store=store,
            transport=transport,
        )

        session._parser.append_buffer(buf)
        return session

    def _on_session_close(self, session_id):
        def _on_close():
            self.sessions.pop(session_id)
        return _on_close

    async def accept_client(
        self,
        reader: aio.StreamReader,
        writer: aio.StreamWriter,
    ) -> None:

        transport = TCPTransport(reader, writer)

        try:
            session = await self.create_session(transport)
        except (
            exc.FIXAuthenticationError,
            exc.UnresponsiveClientError
        ) as error:
            logger.error(error)
            writer.close()
        else:
            session_id = swap_session_id(session.id)
            session.on_close = self._on_session_close(session_id)
            self.sessions[session_id] = session
            # TODO what happens if we hit an invalid
            # (not authentication related) message here
            # await session._process_message(msg)
            self._session_queue.put_nowait(session)

    async def serve(self) -> None:
        host = self.config.host
        port = self.config.port
        self.server = await aio.start_server(
            self.accept_client, host, port)

    async def close(self) -> None:
        if self.server is None:
            return
        for session in list(self.sessions.values()):
            await session.close()
        self.sessions.clear()
        self.server.close()
        await self.server.wait_closed()
        self._session_queue.put_nowait(None)
