import json
import struct
import uuid

import pytest

from fixation.rpc import RPCServer
from fixation.client import FixClient


@pytest.fixture
def fix_client():
    return FixClient()


@pytest.fixture
def rpc_request():
    return {
        'jsonrpc': '2.0',
        'method': 'send_test_request',
        'id': str(uuid.uuid4()),
    }


@pytest.fixture()
def encoded_rpc_request(rpc_request):
    encoded = json.dumps(rpc_request).encode()
    return struct.pack('i', len(encoded)) + encoded


@pytest.fixture()
async def rpc_server(fix_session, fix_client, event_loop):
    return RPCServer(
        fix_client=fix_client,
        loop=event_loop,
    )


def test_handle_rpc_request(rpc_server, rpc_request, encoded_rpc_request):
    pass
