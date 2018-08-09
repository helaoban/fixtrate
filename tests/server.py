import asyncio
import logging

from fixtrate import (
    constants as fc,
    store as fix_store,
    session
)

logger = logging.getLogger(__name__)


class MockFixServer(object):

    def __init__(
        self,
        config=None,
        heartbeat_interval=30,
        loop=None,
        store=None
    ):
        self._store = store or fix_store.FixMemoryStore()
        self._config = config or {
            'HOST': 'localhost',
            'ACCOUNT': 'U001',
            'PORT': 8686,
            'SENDER_COMP_ID': 'FIXTEST',
            'VERSION': fc.FixVersion.FIX42,
            'TARGET_COMP_ID': 'TESTCLIENT',
        }
        self._heartbeat_interval = heartbeat_interval
        self._loop = loop or asyncio.get_event_loop()
        self._tags = getattr(fc.FixTag, self._config['VERSION'].name)
        self._server = None
        self._clients = {}

    async def handle_client(self, session):
        try:
            async for msg in session:
                pass
        except asyncio.CancelledError:
            pass
        finally:
            await session.close()

    async def accept_client(self, reader, writer):
        fix_session = session.FixSession(
            version=fc.FixVersion.FIX42,
            sender_comp_id='TESTSERVER',
            target_comp_id='TESTCLIENT',
            heartbeat_interval=self._heartbeat_interval,
            store=self._store,
            loop=self._loop
        )
        await fix_session.listen(reader, writer)
        task = self._loop.create_task(
            self.handle_client(fix_session))
        self._clients[task] = fix_session

    async def start(self):
        host = self._config.get('HOST', '127.0.0.1')
        port = self._config.get('PORT', 4000)
        self._server = await asyncio.start_server(
            self.accept_client,
            host=host,
            port=port,
        )

    async def close(self):
        for task, fix_session in self._clients.items():
            task.cancel()
            await task

        self._server.close()
        await self._server.wait_closed()
