import asyncio
from async_timeout import timeout as aiotimeout
from collections.abc import Coroutine
import logging

from . import constants as fix
from .parse import FixParser
from .exceptions import (
    FIXAuthenticationError, BindClosedError,
    UnresponsiveClientError, DuplicateSessionError
)
from .store import MemoryStoreInterface
from .session import FixSession
from .transport import TCPTransport, TCPListenerTransport
from .helpers import parse_session_id_from_conf

logger = logging.getLogger(__name__)


DEFAULT_OPTIONS = {
}


def get_options(**kwargs):

    rv = dict(DEFAULT_OPTIONS)
    options = dict(**kwargs)

    for key, value in options.items():
        if key not in rv:
            raise TypeError("Unknown option %r" % (key,))
        rv[key] = value

    return rv


class FixEngine:

    def __init__(self, **options):
        self.config = get_options(**options)
        self.store_interface = MemoryStoreInterface()

        self.sessions = []
        self.binds = []

    async def _on_session_connect(self, session):
        self.sessions.append(session)

    async def _on_bind(self, bind):
        self.binds.append(bind)

    def connect(self, host, port, conf):
        """
        Coroutine that waits for a successfuly connection to a FIX peer.
        Returns a FixConnection object. Can also be used as an async context
        manager, in which case the connection is automatically closed on
        exiting the context manager.

        :param address: tuple of (ip, port)
        :return: :class:`FixConnection` object
        :rtype: FixConnection
        """
        return _FixConnectionManager(
            engine=self,
            host=host,
            port=port,
            session_conf=conf,
            on_connect=self._on_session_connect
        )

    def bind(self, host, port, session_confs):
        return _FixBindManager(
            engine=self,
            host=host,
            port=port,
            session_confs=session_confs,
            on_bind=self._on_bind
        )

    async def close(self):
        for session in self.sessions:
            await session.close()
        self.sessions.clear()
        for bind in self.binds:
            await bind.close()
        self.binds.clear()
        await self.store_interface.close(self)


class _FixConnectionManager(Coroutine):

    def __init__(
        self,
        engine,
        host,
        port,
        session_conf,
        on_connect=None
    ):
        self.engine = engine
        self.host = host
        self.port = port
        self.session_conf = session_conf

        self.transport = TCPTransport()
        self.session = None
        self._on_connect = on_connect
        self._coro = self._make_session()

    def __await__(self):
        return self._coro.__await__()

    async def __aenter__(self):
        return await self._coro

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            logger.error(exc_val)
            await self.session.close()
            return False
        else:
            await self._wait_for_logout(self.session)
        await self.session.close()

    def send(self, arg):
        self._coro.send(arg)

    def throw(self, typ, val=None, tb=None):
        self._coro.throw(typ, val, tb)

    def close(self):
        self._coro.close()

    async def _wait_for_logout(self, session):
        if session.logged_on:
            await session.logout()
            while True:
                with aiotimeout(5):
                    msg = await session.receive(timeout=5)
                    if msg.msg_type == fix.FixMsgType.LOGOUT:
                        break

    async def _make_session(self):
        session_id, conf = parse_session_id_from_conf(
            self.session_conf)
        store_if = self.engine.store_interface
        store = await store_if.connect(self.engine)
        await self.transport.connect(self.host, self.port)
        session = FixSession(
            session_id=session_id,
            store=store,
            transport=self.transport,
            **conf
        )
        if self._on_connect is not None:
            await self._on_connect(session)
        self.session = session
        return session


class FixBind:
    def __init__(
        self,
        engine,
        host,
        port,
        session_confs,
    ):
        self.engine = engine
        self.host = host
        self.port = port
        self.sessions = {}
        self.server = None

        self._allowed_sessions = self._parse_session_confs(
            session_confs)
        self._session_queue = asyncio.Queue()

    @staticmethod
    def _parse_session_confs(confs):
        ids = {}
        for c in confs:
            sid, conf = parse_session_id_from_conf(c)
            ids[sid.target] = sid, conf
        return ids

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return await self.get_session()
        except (asyncio.CancelledError, BindClosedError) as error:
            logger.error(error)
            raise StopAsyncIteration

    async def get_session(self):
        session = await self._session_queue.get()
        if session is None:
            raise BindClosedError
        return session

    def _on_session_close(self, session):
        self.sessions.pop(session.id, None)

    def _authenticate_client(self, msg):
        begin_string = msg.get(8)
        try:
            fix_version = fix.FixVersion(begin_string)
        except ValueError as error:
            raise FIXAuthenticationError(
                '%s in an invalid or unsupported FIX version'
                '' % begin_string
            ) from error

        sender = msg.get(fix.FixTag.SenderCompID)
        try:
            session_id, conf = self._allowed_sessions[sender]
        except KeyError as error:
            raise FIXAuthenticationError(
                'No session with SenderCompID of %s was found '
                '' % sender
            ) from error

        if session_id in self.sessions:
            raise DuplicateSessionError

        if begin_string != session_id.begin_string:
            raise FIXAuthenticationError(
                'Expected %s as value for BeginStr, but got %s '
                '' % (session_id.begin_string, begin_string)
            )

        target = msg.get(fix.FixTag.TargetCompID)
        if target != session_id.sender:
            raise FIXAuthenticationError(
                'Expected %s as value for TargetCompId, but got %s '
                '' % (session_id.target, target)
            )
        return session_id, conf

    async def _create_store(self):
        return await self.engine.store_interface.connect(
            self.engine)

    async def _read_client_data(self, transport):
        try:
            # TODO How long to wait for Logon msg after TCP
            # connection made?
            with aiotimeout(1):
                data = await transport.read()
        except asyncio.TimeoutError as error:
            raise UnresponsiveClientError from error
        return data

    async def _create_client_session(self, reader, writer):
        transport = TCPListenerTransport()
        await transport.connect(reader, writer)

        parser, session_parser = FixParser(), FixParser()
        while True:
            msg = parser.get_message()
            if msg:
                break
            data = await self._read_client_data(transport)
            parser.append_buffer(data)
            session_parser.append_buffer(data)

        session_id, conf = self._authenticate_client(msg)
        store = await self._create_store()
        session = FixSession(
            session_id=session_id,
            store=store,
            transport=transport,
            initiator=False,
            on_close=self._on_session_close,
            **conf
        )
        session.parser = session_parser
        return session

    async def _accept_client(self, reader, writer):
        try:
            session = await self._create_client_session(reader, writer)
        except (FIXAuthenticationError, UnresponsiveClientError) as error:
            logger.error(error)
            writer.close()
        except Exception as error:
            logger.exception(error)
            await self.close()
        else:
            self.sessions[session.id] = session
            # TODO what happens if we hit an invalid
            # (not authentication related) message here
            # await session._process_message(msg)
            self._session_queue.put_nowait(session)

    async def bind(self):
        self.server = await asyncio.start_server(
            self._accept_client, self.host, self.port)

    async def close(self):
        self.server.close()
        for session in list(self.sessions.values()):
            await session.close()
        await self.server.wait_closed()
        self._session_queue.put_nowait(None)


class _FixBindManager(Coroutine):

    def __init__(
        self,
        engine,
        host,
        port,
        session_confs,
        on_bind=None
    ):
        self.engine = engine
        self.host = host
        self.port = port
        self.session_confs = session_confs
        self._on_bind = on_bind
        self.bind = None
        self._coro = self._start()

    def __await__(self):
        return self._coro.__await__()

    def send(self, arg):
        self._coro.send(arg)

    def throw(self, typ, val=None, tb=None):
        self._coro.throw(typ, val, tb)

    def close(self):
        self._coro.close()

    async def __aenter__(self):
        await self._coro
        return self.bind

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.bind.close()

    async def _start(self):
        self.bind = FixBind(
            self.engine, self.host,
            self.port, self.session_confs)
        await self.bind.bind()
        if self._on_bind is not None:
            await self._on_bind(self.bind)
        return self.bind
