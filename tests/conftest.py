import pytest

import fixtrate.constants
from fixtrate import (
    constants as c,
    parse,
    store,
    session
)
# from fixtrate import parse, store, session
from tests.server import MockFixServer


@pytest.fixture
def client_store():
    return store.FixMemoryStore()


@pytest.fixture
def server_store():
    return store.FixMemoryStore()


@pytest.fixture
def server_config():
    return dict(
        HOST='127.0.0.1',
        ACCOUNT='U001',
        PORT=8686,
        SENDER_COMP_ID='TESTSERVER',
        VERSION=c.FixVersion.FIX42,
        TARGET_COMP_ID='TESTCLIENT',
        HEARTBEAT_INTERVAL=30
    )


@pytest.fixture
@pytest.mark.asyncio
async def test_server(event_loop, server_store, server_config):
    server = MockFixServer(
        config=server_config,
        loop=event_loop,
        store=server_store
    )
    await server.start()
    yield server
    await server.close()


@pytest.fixture
def parser():
    return parse.FixParser()


@pytest.fixture
async def fix_session(client_store, event_loop):
    return session.FixSession(
        version=c.FixVersion.FIX42,
        sender_comp_id='TESTCLIENT',
        target_comp_id='TESTSERVER',
        heartbeat_interval=30,
        store=client_store,
        loop=event_loop
    )


@pytest.fixture
async def fix_endpoint():
    return 'localhost', 8686
