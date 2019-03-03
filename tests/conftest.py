import asyncio
import aioredis
import pytest
from fixtrate import constants as fix
from tests.server import MockFixServer
from fixtrate.store import MemoryStoreInterface, RedisStoreInterface
from fixtrate.engine import FixEngine


@pytest.fixture(params=['inmemory', 'redis'])
async def store_interface(request):
    redis_url = 'redis://localhost:6379'
    prefix = 'fix-test'
    if request.param == 'redis':
        store_interface = RedisStoreInterface(redis_url, prefix)
    else:
        store_interface = MemoryStoreInterface()
    yield store_interface
    if request.param == 'redis':
        client = await aioredis.create_redis(redis_url)
        keys = await client.keys('%s*' % prefix)
        if keys:
            await client.delete(*keys)
        client.close()


@pytest.fixture
def client_config():
    config = {
        'begin_string': fix.FixVersion.FIX42,
        'sender_comp_id': 'TESTCLIENT',
        'target_comp_id': 'TESTSERVER',
        'heartbeat_interval': 30,
    }
    return config


@pytest.fixture
def server_config(request, store_interface):
    overrides = getattr(request, 'param', {})
    return {
        'host': '127.0.0.1',
        'port': 8686,
        'client_session_confs': [{
            'begin_string': fix.FixVersion.FIX42,
            'sender_comp_id': 'TESTSERVER',
            'target_comp_id': 'TESTCLIENT',
            'heartbeat_interval': 30,
        }],
        'store': store_interface,
        **overrides
    }


@pytest.fixture
async def test_server(request, server_config):
    server = MockFixServer(server_config)
    asyncio.get_event_loop().create_task(server.listen())
    yield server
    await server.close()


@pytest.fixture
async def engine(store_interface):
    engine = FixEngine()
    engine.store_interface = store_interface
    yield engine
    await engine.close()
