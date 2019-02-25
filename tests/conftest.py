import aioredis
import pytest

from fixtrate.constants import FixVersion
from tests.server import MockFixServer
from fixtrate.session import FixSession
from fixtrate.store import FixMemoryStore, FixRedisStore
from fixtrate.transport import TCPTransport

VERSION = FixVersion.FIX42


class TCPListenerTransport(TCPTransport):
    async def connect(self, host, port):
        self.reader = self.options['reader']
        self.writer = self.options['writer']


@pytest.fixture(params=['inmemory', 'redis'])
async def store_config(request):
    redis_url = 'redis://localhost:6379'
    prefix = 'fix-test'
    yield {
        'inmemory': {
            'store': FixMemoryStore,
            'store_options': {}
        },
        'redis': {
            'store': FixRedisStore,
            'store_options': {
                'redis_url': redis_url,
                'prefix': prefix
            }
        }
    }.get(request.param)
    redis = await aioredis.create_redis(redis_url)
    keys = await redis.keys('fix-test:*')
    if len(keys):
        await redis.delete(*keys)


@pytest.fixture
def server_config(store_config):
    config = {
        'host': '127.0.0.1',
        'port': 8686,
        'session_config': {
            'fix_version': VERSION,
            'sender_comp_id': 'TESTSERVER',
            'target_comp_id': 'TESTCLIENT',
            'heartbeat_interval': 30,
            'transport': TCPListenerTransport,
            **store_config
        }
    }    
    return config


@pytest.fixture
async def test_server(server_config):
    server = MockFixServer(server_config)
    await server.start()
    yield server
    await server.close()


@pytest.fixture
def client_config(store_config):
    config = {
        'fix_version': VERSION,
        'sender_comp_id': 'TESTCLIENT',
        'target_comp_id': 'TESTSERVER',
        'heartbeat_interval': 30,
        'host': '127.0.0.1',
        'port': 8686,
        **store_config
    }
    return config


@pytest.fixture
async def fix_session(client_config):
    yield FixSession(**client_config)
