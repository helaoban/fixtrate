import asyncio
import logging

from fixation import (
    constants as fc,
    store as fix_store,
    session
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
        self.TAGS = getattr(fc.FixTag, self.config['FIX_VERSION'].name)

        self._hearbeat_cb = None

        self._listener = None

    async def listen(self):
        self.session = session.FixSession(
            conf=self.config,
            store=self.store,
            loop=self.loop,
        )

        async with self.session.listen():
            async for msg in self.session:
                pass

    def start(self):
        self._listener = self.loop.create_task(self.listen())

    def close(self):
        self._listener.cancel()

    async def wait_close(self):
        try:
            await self._listener
        except asyncio.CancelledError:
            pass
