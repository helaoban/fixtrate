import pytest
import aioredis

from fixtrate.config import Config, default_config
from fixtrate.constants import FixVersion
from fixtrate.parse import FixParser
from tests.server import MockFixServer
from fixtrate.session import FixSession
from fixtrate.store import FixMemoryStore, FixRedisStore

VERSION = FixVersion.FIX42


@pytest.fixture(params=['inmemory', 'redis'])
async def store(request):
    if request.param == 'redis':
        url = 'redis://localhost:6379'
        redis = await aioredis.create_redis(url)

        yield FixRedisStore(redis, prefix='fix_test:')

        # cleanup
        to_delete = await redis.keys('fix_test:*')
        if len(to_delete) > 0:
            await redis.delete(*to_delete)

        redis.close()
        await redis.wait_closed()
    else:
        yield FixMemoryStore()


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
async def test_server(store, server_config):
    server = MockFixServer(
        config=server_config,
        store=store,
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
async def fix_session(client_config, store):
    session = FixSession()
    session.config = client_config
    session.store = store
    return session


@pytest.fixture
async def fix_endpoint():
    return 'localhost', 8686
