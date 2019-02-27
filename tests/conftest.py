import asyncio
import pytest
from fixtrate import constants as fix
from tests.server import MockFixServer
from fixtrate.store import MemoryStoreInterface, RedisStoreInterface
from fixtrate.engine import FixEngine


@pytest.fixture(params=['inmemory', 'redis'])
async def store_interface(request):
    store_interface = MemoryStoreInterface()
    if request.param == 'redis':
        url = 'redis://localhost:6379'
        prefix = 'fix-test'
        store_interface = RedisStoreInterface(url, prefix)
    return store_interface


@pytest.fixture
def client_config():
    config = {
        'fix_version': fix.FixVersion.FIX42,
        'sender_comp_id': 'TESTCLIENT',
        'target_comp_id': 'TESTSERVER',
        'heartbeat_interval': 30,
    }
    return config


@pytest.fixture
def server_config(request):
    overrides = getattr(request, 'param', {})
    return {
        'host': '127.0.0.1',
        'port': 8686,
        'client_session_confs': [{
            'fix_version': fix.FixVersion.FIX42,
            'sender_comp_id': 'TESTSERVER',
            'target_comp_id': 'TESTCLIENT',
            'heartbeat_interval': 30,
        }],
        **overrides
    }


@pytest.fixture
async def test_server(request, server_config):
    server = MockFixServer(server_config)
    asyncio.get_event_loop().create_task(server.listen())
    yield server
    await server.close()


@pytest.fixture
async def engine():
    engine = FixEngine()
    yield engine
    await engine.close()
