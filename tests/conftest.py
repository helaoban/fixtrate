import pytest

import fixation.constants
from fixation import parse, store, session
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
        SENDER_COMP_ID='FIXTEST',
        VERSION=fixation.constants.FixVersion.FIX42,
        TARGET_COMP_ID='TESTCLIENT',
        HEARTBEAT_INTERVAL=1
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
def client_config(server_config):
    return {
        **server_config,
        'TARGET_COMP_ID': server_config['SENDER_COMP_ID'],
        'SENDER_COMP_ID': 'TESTCLIENT',
        'ACCOUNT': 'account',
        'RESET_SEQUENCE': True
    }


@pytest.fixture
def parser(client_config):
    return parse.FixParser(client_config)


@pytest.fixture
async def fix_session(client_config, client_store):
    return session.FixSession(client_config, store=client_store)
