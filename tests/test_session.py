import asyncio
import pytest
import uuid

from fixtrate import constants as fix
from fixtrate.message import FixMessage
from fixtrate.factories import fix42

TAGS = fix.FixTag.FIX42


@pytest.fixture
def test_request():
    id_ = str(uuid.uuid4())
    return fix42.test_request(id_)


@pytest.fixture
def news_msg():
    pairs = (
        (TAGS.MsgType, fix.FixMsgType.NEWS, True),
        (TAGS.Headline, 'BREAKING NEWS', False),
        (TAGS.LinesOfText, 1, False),
        (TAGS.Text, 'Government admits turning frogs gay.', False),
    )
    return FixMessage.from_pairs(pairs)


@pytest.mark.asyncio
async def test_can_login_logout(engine, test_server, client_config):
    host = test_server.config['host']
    port = test_server.config['port']
    async with engine.connect(host, port, client_config) as session:
        await session.logon()
        msg = await session.receive(timeout=0.1)
        assert msg.msg_type == fix.FixMsgType.LOGON
        assert msg.get(56) == client_config['sender_comp_id']

        await session.logout()
        msg = await session.receive(timeout=0.1)
        assert msg.msg_type == fix.FixMsgType.LOGOUT


@pytest.mark.asyncio
async def test_auto_logs_out(engine, test_server, client_config):
    host = test_server.config['host']
    port = test_server.config['port']
    async with engine.connect(host, port, client_config) as session:
        await session.logon()
        msg = await session.receive(timeout=0.1)
        assert msg.msg_type == fix.FixMsgType.LOGON
        assert msg.get(56) == client_config['sender_comp_id']

    assert not session.logged_on


@pytest.mark.asyncio
async def test_can_iterate(
    engine, test_server, client_config, test_request):

    host = test_server.config['host']
    port = test_server.config['port']
    async with engine.connect(host, port, client_config) as session:
        await session.logon()
        async for msg in session:
            assert msg.msg_type == fix.FixMsgType.LOGON
            break

        await session.send(test_request)

        async for msg in session:
            assert msg.msg_type == fix.FixMsgType.HEARTBEAT
            assert msg.get(TAGS.TestReqID) == test_request.get(TAGS.TestReqID)
            break


@pytest.mark.asyncio
async def test_does_not_allow_second_connection(
    engine, test_server, client_config
):

    host = test_server.config['host']
    port = test_server.config['port']
    session = await engine.connect(host, port, client_config)
    await session.logon()
    _ = await session.receive()

    with pytest.raises(ConnectionAbortedError):
        session2 = await engine.connect(host, port, client_config)
        await session2.logon()
        _ = await session2.receive()


@pytest.mark.asyncio
async def test_receive_timeout(engine, test_server, client_config):

    host = test_server.config['host']
    port = test_server.config['port']
    async with engine.connect(host, port, client_config) as session:
        await session.logon()

        msg = await session.receive()
        assert msg.msg_type == fix.FixMsgType.LOGON
        with pytest.raises(asyncio.TimeoutError):
            await session.receive(timeout=0.1)


@pytest.mark.parametrize(
    'server_config',
    [
        {
            'client_session_confs': [
                {
                    'begin_string': fix.FixVersion.FIX42,
                    'sender_comp_id': 'TESTSERVER',
                    'target_comp_id': 'TESTCLIENT',
                    'heartbeat_interval': 1,
                }
            ]
        }
    ],
    indirect=True
)
@pytest.mark.asyncio
async def test_heartbeat(engine, test_server, client_config):
    client_config['heartbeat_interval'] = 1
    host = test_server.config['host']
    port = test_server.config['port']
    async with engine.connect(host, port, client_config) as session:
        await session.logon()

        msg = await session.receive(timeout=0.1)
        assert msg.msg_type == fix.FixMsgType.LOGON
        msg = await session.receive(timeout=1.2)
        assert msg.msg_type == fix.FixMsgType.HEARTBEAT


@pytest.mark.asyncio
async def test_incorrect_heartbeat_int(engine, test_server, client_config):
    client_config['heartbeat_interval'] = 90
    host = test_server.config['host']
    port = test_server.config['port']
    async with engine.connect(host, port, client_config) as session:
        await session.logon()
        msg = await session.receive(timeout=0.1)
        assert msg.msg_type == fix.FixMsgType.REJECT
        assert int(msg.get(TAGS.RefTagID)) == TAGS.HeartBtInt


@pytest.mark.asyncio
async def test_incorrect_target_comp_id(engine, test_server, client_config):
    client_config['target_comp_id'] = 'not-a-correct-id'
    host = test_server.config['host']
    port = test_server.config['port']
    async with engine.connect(host, port, client_config) as session:
        await session.logon()
        with pytest.raises(ConnectionAbortedError):
            await session.receive(timeout=0.1)


@pytest.mark.asyncio
async def test_incorrect_sender_comp_id(engine, test_server, client_config):
    client_config['sender_comp_id'] = 'not-a-correct-id'
    host = test_server.config['host']
    port = test_server.config['port']
    async with engine.connect(host, port, client_config) as session:
        await session.logon()
        with pytest.raises(ConnectionAbortedError):
            await session.receive(timeout=0.1)


@pytest.mark.asyncio
async def test_test_request(
    engine, test_server, client_config, test_request):

    test_id = str(uuid.uuid4())

    host = test_server.config['host']
    port = test_server.config['port']
    async with engine.connect(host, port, client_config) as session:
        await session.logon()
        await session.send(test_request)

        msg = await session.receive()
        assert msg.msg_type == fix.FixMsgType.LOGON

        msg = await session.receive()
        assert msg.msg_type == fix.FixMsgType.HEARTBEAT
        assert msg.get(TAGS.TestReqID) == test_request.get(TAGS.TestReqID)


@pytest.mark.asyncio
async def test_reset_seq_num(
    engine, test_server, client_config, test_request):

    host = test_server.config['host']
    port = test_server.config['port']
    async with engine.connect(host, port, client_config) as session:
        await session.logon()

        msg = await session.receive()
        assert msg.msg_type == fix.FixMsgType.LOGON

        test_id = str(uuid.uuid4())
        await session.send(test_request)
        msg = await session.receive()
        assert msg.msg_type == fix.FixMsgType.HEARTBEAT
        assert msg.get(TAGS.TestReqID) == test_request.get(TAGS.TestReqID)
        await session.logon(reset=True)

        msg = await session.receive()
        local_seq_num = await session.get_local_sequence()

        assert msg.msg_type == fix.FixMsgType.LOGON
        assert msg.get(TAGS.ResetSeqNumFlag) == fix.ResetSeqNumFlag.YES
        assert msg.seq_num == 1
        assert local_seq_num == 2


@pytest.mark.asyncio
async def test_sequence_reset(
    engine, test_server, client_config, test_request):

    host = test_server.config['host']
    port = test_server.config['port']
    async with engine.connect(host, port, client_config) as session:
        await session.logon()

        msg = await session.receive()
        assert msg.msg_type == fix.FixMsgType.LOGON

        # TODO This is dumb, find a better way to test a hard
        # reset
        server_session = test_server.client_sessions[0]
        await server_session._set_local_sequence(9)
        sequence_reset = server_session._make_sequence_reset(10)
        await server_session.send(sequence_reset)

        msg = await session.receive()
        assert msg.msg_type == fix.FixMsgType.SEQUENCE_RESET

        new_remote_seq_num = int(msg.get(TAGS.NewSeqNo))
        assert new_remote_seq_num == await session.get_remote_sequence()

        await session.send(test_request)
        msg = await session.receive()
        assert msg.msg_type == fix.FixMsgType.HEARTBEAT
        assert msg.get(TAGS.TestReqID) == test_request.get(TAGS.TestReqID)


@pytest.mark.parametrize(
    'server_config',
    [
        {
            'client_session_confs': [
                {
                    'begin_string': fix.FixVersion.FIX42,
                    'sender_comp_id': 'TESTSERVER',
                    'target_comp_id': 'TESTCLIENT',
                    'heartbeat_interval': 1,
                }
            ]
        }
    ],
    indirect=True
)
@pytest.mark.asyncio
async def test_message_recovery(
    engine, test_server, client_config, news_msg):

    client_config['heartbeat_interval'] = 1
    host = test_server.config['host']
    port = test_server.config['port']

    with pytest.raises(ConnectionAbortedError):
        async with engine.connect(host, port, client_config) as session:
            await session.logon()

            msg = await session.receive()
            assert msg.msg_type == fix.FixMsgType.LOGON

            await test_server.client_sessions[0].send(news_msg)
            raise ConnectionAbortedError

    async with engine.connect(host, port, client_config) as session:
        await session.logon()

        # the logon msg
        msg = await session.receive()
        assert msg.msg_type == fix.FixMsgType.LOGON

        # the news msg
        msg = await session.receive()
        assert msg.msg_type == fix.FixMsgType.NEWS
        # gap fill for the second logon msg
        msg = await session.receive()
        assert msg.msg_type == fix.FixMsgType.SEQUENCE_RESET

        # the next message should process fine
        msg = await session.receive()
        assert msg.msg_type == fix.FixMsgType.HEARTBEAT

