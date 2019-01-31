import pytest

from fixtrate.config import Config, default_config
from fixtrate.constants import FixVersion
from fixtrate.parse import FixParser
from tests.server import MockFixServer
from fixtrate.session import FixSession
from fixtrate.store import FixMemoryStore

VERSION = FixVersion.FIX42


@pytest.fixture
def client_store():
    return FixMemoryStore()


@pytest.fixture
def server_store():
    return FixMemoryStore()


@pytest.fixture
def server_config():
    config = Config(default_config)
    config['VERSION'] = VERSION
    config['SENDER_COMP_ID'] = 'TESTSERVER'
    config['TARGET_COMP_ID'] = 'TESTCLIENT'
    config['HEARTBEAT_INTERVAL'] = 30
    config['HOST'] = '127.0.0.1'
    config['PORT'] = 8686
    config['ACCOUNT'] = 'U001'
    return config


@pytest.fixture
@pytest.mark.asyncio
async def test_server(event_loop, server_store, server_config):
    server = MockFixServer(
        config=server_config,
        store=server_store,
    )
    await server.start()
    yield server
    await server.close()


@pytest.fixture
def parser():
    return FixParser()


@pytest.fixture
def client_config():
    config = Config(default_config)
    config['VERSION'] = VERSION
    config['SENDER_COMP_ID'] = 'TESTCLIENT'
    config['TARGET_COMP_ID'] = 'TESTSERVER'
    config['HEARTBEAT_INTERVAL'] = 30
    return config


@pytest.fixture
async def fix_session(client_config, client_store, event_loop):
    session = FixSession()
    session.config = client_config
    session.store = client_store
    return session


@pytest.fixture
async def fix_endpoint():
    return 'localhost', 8686
