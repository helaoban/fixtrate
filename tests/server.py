import asyncio
import logging
from fixtrate.engine import FixEngine
logger = logging.getLogger(__name__)


class MockFixServer(object):

    def __init__(self, config):
        self.config = config
        self.engine = FixEngine()
        self.client_sessions = []
        self.tasks = []

    async def stream_client_session(self, session):
        try:
            async for msg in session:
                # print(msg)
                pass
        except asyncio.CancelledError:
            pass

    async def listen(self):
        host, port = self.config['host'], self.config['port']
        session_confs = self.config['client_session_confs']
        async with self.engine.bind(host, port, session_confs) as bind:
            async for session in bind:
                self.client_sessions.append(session)
                coro = self.stream_client_session(session)
                task = asyncio.get_event_loop().create_task(coro)
                self.tasks.append(task)

    async def close(self):
        await self.engine.close()
        self.client_sessions.clear()
