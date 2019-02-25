import asyncio
import logging
from fixtrate.session import FixSession

logger = logging.getLogger(__name__)


class MockFixServer(object):

    def __init__(self, config):
        self.config = config
        self.server = None
        self.client_sessions = {}
        self.tasks = []

    async def stream_client(self, session):
        try:
            async with session.connect():
                async for msg in session:
                    print(msg)
                    # pass
        except asyncio.CancelledError:
            pass

    async def accept_client(self, reader, writer):
        peer = writer.transport.get_extra_info('peername')
        transport_conf = dict(reader=reader, writer=writer)
        try:
            session = self.client_sessions[peer]
            session.config['transport_options'] = transport_conf
        except KeyError:
            session_conf = self.config['session_config']
            session_conf['transport_options'] = transport_conf
            session = FixSession(**session_conf)
            self.client_sessions[peer] = session

        asyncio.get_event_loop().create_task(
            self.stream_client(session))

    def update_session_conf(self, new_conf):
        self.config['session_config'].update(new_conf)

    async def start(self):
        host, port = self.config.get('host'), self.config.get('port')
        self.server = await asyncio.start_server(
            self.accept_client,
            host=host,
            port=port,
        )

    async def close(self):
        for session in self.client_sessions.values():
            await session.close()
        self.server.close()
        await self.server.wait_closed()
