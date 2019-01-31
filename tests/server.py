import asyncio
import logging
from fixtrate.session import FixSession
from fixtrate.store import FixMemoryStore

logger = logging.getLogger(__name__)


class MockFixServer(object):

    def __init__(
        self,
        config,
        heartbeat_interval=30,
        store=None
    ):
        self.store = store or FixMemoryStore()
        self.config = config
        self.server = None
        self.clients = {}

    async def handle_client(self, session):
        try:
            async for msg in session:
                pass
        except asyncio.CancelledError:
            pass
        finally:
            await session.close()

    async def accept_client(self, reader, writer):
        fix_session = FixSession()
        fix_session.config = self.config
        fix_session.store = self.store
        await fix_session.listen(reader, writer)

        loop = asyncio.get_event_loop()
        task = loop.create_task(
            self.handle_client(fix_session))
        self.clients[task] = fix_session

    async def start(self):
        host = self.config.get('HOST', '127.0.0.1')
        port = self.config.get('PORT', 4000)
        self.server = await asyncio.start_server(
            self.accept_client,
            host=host,
            port=port,
        )

    async def close(self):
        for task, fix_session in self.clients.items():
            task.cancel()
            await task

        self.server.close()
        await self.server.wait_closed()
