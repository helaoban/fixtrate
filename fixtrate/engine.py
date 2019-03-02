import asyncio
from async_timeout import timeout as aiotimeout
from collections.abc import Coroutine
import logging

from . import constants as fix
from .parse import FixParser
from .exceptions import FIXAuthenticationError, BindClosedError
from .store import MemoryStoreInterface
from .session import FixSession
from .transport import TCPTransport, TCPListenerTransport


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

    def connect(self, host, port, conf, transport=None):
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
            self, host, port, conf,
            on_connect=self._on_session_connect)

    def bind(self, host, port, session_confs):
        return _FixBindManager(
            self, host, port, session_confs,
            on_bind=self._on_bind
        )

    async def close(self):
        for session in self.sessions:
            await session.close()
        self.sessions.clear()

        for bind in self.binds:
            await bind.close()
        self.binds.clear()


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
        if isinstance(exc_val, ConnectionError):
            await self.session.close()
            return False
        await self._wait_for_logout(self.session)
        await self.session.close()
        return True

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
        store_if = self.engine.store_interface
        store = await store_if.connect(self.engine)
        await self.transport.connect(self.host, self.port)
        session = FixSession(
            store, self.transport, **self.session_conf)
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
        self.session_confs = {
            c['target_comp_id']: c
            for c in session_confs
        }
        self.sessions = {}
        self._session_queue = asyncio.Queue()
        self.server = None

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
        sender = msg.get(49)
        try:
            conf = self.session_confs[sender]
        except KeyError as error:
            raise FIXAuthenticationError from error

        target = msg.get(56)
        if target != conf['sender_comp_id']:
            raise FIXAuthenticationError

        # TODO should an incorrect begin_string
        # really result in a connection termination?
        # Or should we send a reject message.
        begin_string = msg.get(8)
        if begin_string != conf['fix_version']:
            raise FIXAuthenticationError

        return conf

    async def _accept_client(self, reader, writer):
        store_if = self.engine.store_interface
        store = await store_if.connect(self.engine)

        transport = TCPListenerTransport()
        await transport.connect(reader, writer)

        parser, session_parser = FixParser(), FixParser()
        while True:
            msg = parser.get_message()
            if msg:
                break
            try:
                # TODO How long to wait for Logon msg after TCP
                # connection made?
                with aiotimeout(1):
                    data = await transport.read()
            except (asyncio.CancelledError, asyncio.TimeoutError):
                raise asyncio.TimeoutError
            parser.append_buffer(data)
            session_parser.append_buffer(data)

        try:
            conf = self._authenticate_client(msg)
        except FIXAuthenticationError:
            writer.close()
            return

        session = FixSession(
            store, transport,
            initiator=False,
            on_close=self._on_session_close,
            **conf)

        # TODO this is probably technically
        # an authentication error and should be
        # part of the _authenticate handler,
        # but need reliable way to get session_id
        # before instantiation a session
        if session.id in self.sessions:
            writer.close()
            return

        session.parser = session_parser
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
