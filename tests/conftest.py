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
        FIX_HOST='127.0.0.1',
        FIX_PORT=8686,
        FIX_SENDER_COMP_ID='FIXTEST',
        FIX_VERSION=fixation.constants.FixVersion.FIX42,
        FIX_TARGET_COMP_ID='TESTCLIENT',
        FIX_HEARTBEAT_INTERVAL=1
    )


@pytest.fixture
@pytest.mark.asyncio
async def test_server(event_loop, server_store, server_config):
    server = MockFixServer(
        config=server_config,
        loop=event_loop,
        store=server_store
    )
    server()
    yield server
    server.shutdown()


@pytest.fixture
def client_config(server_config):
    return {
        **server_config,
        'FIX_TARGET_COMP_ID': server_config['FIX_SENDER_COMP_ID'],
        'FIX_SENDER_COMP_ID': 'TESTCLIENT',
        'FIX_ACCOUNT': 'account',
        'FIX_HEARTBEAT_INTERVAL': 1,
        'FIX_RESET_SEQUENCE': True
    }


@pytest.fixture
def parser(client_config):
    return parse.FixParser(client_config)


@pytest.fixture
async def fix_session(client_config, client_store, test_server):
    return session.FixSession(client_config, store=client_store)

