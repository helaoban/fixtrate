import pytest

from fixation import config, version, parse, store, session
from tests.server import MockFixServer


@pytest.fixture
def client_store():
    return store.FixMemoryStore()


@pytest.fixture
def server_store():
    return store.FixMemoryStore()


@pytest.fixture
def server_config():
    return config.FixConfig(
        host='localhost',
        port=8686,
        sender_comp_id='FIXTEST',
        version=version.FixVersion.FIX42,
        target_comp_id='TESTCLIENT'
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
    return config.FixConfig(
        host=server_config.host,
        port=server_config.port,
        target_comp_id=server_config.sender_comp_id,
        version=server_config.version,
        sender_comp_id='TESTCLIENT'
    )


@pytest.fixture
def parser(client_config):
    return parse.FixParser(client_config)


@pytest.fixture
async def fix_session(client_config, client_store, test_server):
    return session.FixSession(client_config, store=client_store)

