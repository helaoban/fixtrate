import asyncio
import logging

from fixation import (
    constants as fc,
    store as fix_store,
    session, utils
)

logger = logging.getLogger(__name__)


class MockFixServer(object):

    def __init__(self, config=None, loop=None, store=None):
        self.reader = None
        self.writer = None
        self.store = store or fix_store.FixMemoryStore()
        self.config = config or {
            'FIX_HOST': 'localhost',
            'FIX_ACCOUNT': 'U001',
            'FIX_PORT': 8686,
            'FIX_SENDER_COMP_ID': 'FIXTEST',
            'FIX_VERSION': fc.FixVersion.FIX42,
            'FIX_TARGET_COMP_ID': 'TESTCLIENT',
        }
        self.session = None
        self.loop = loop or asyncio.get_event_loop()
        self._closing = False

        self._last_message_time = None
        self._tags = getattr(fc.FixTag, self.config['FIX_VERSION'].name)

        self._hearbeat_cb = None
        self._server = None
        self._clients = []

    async def send_message(self, msg):
        await self.session.send_message(msg)

    async def handle_client(self, session):
        try:
            async for msg in session:
                # print('SERVER RECEIVED: {}'.format(msg))
                pass
        except asyncio.CancelledError:
            pass
        finally:
            await session.close()

    async def accept_client(self, reader, writer):
        fix_session = session.FixSession(
            conf=self.config,
            store=self.store,
            loop=self.loop
        )
        fix_session.listen(reader, writer)

        async for msg in fix_session:
            pass

        task = self.loop.create_task(self.handle_client(fix_session))
        self._clients.append((task, fix_session))

    async def start(self):
        host = self.config.get('FIX_HOST', '127.0.0.1')
        port = self.config.get('FIX_PORT', 4000)
        self._server = await asyncio.start_server(
            self.accept_client,
            host=host,
            port=port,
        )

    async def close(self):
        for task, fix_session in self._clients:
            task.cancel()
            await task

        self._server.close()
        await self._server.wait_closed()
