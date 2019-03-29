import asyncio
import pytest
import uuid

from fixtrate import helpers, constants as fix
from fixtrate.message import FixMessage
from fixtrate.factories import fix42


@pytest.fixture
def test_request():
    id_ = str(uuid.uuid4())
    return fix42.test_request(id_)


@pytest.fixture
def news_msg():
    pairs = (
        (fix.FixTag.MsgType, fix.FixMsgType.NEWS, True),
        (fix.FixTag.Headline, 'BREAKING NEWS', False),
        (fix.FixTag.LinesOfText, 1, False),
        (fix.FixTag.Text, 'Government admits turning frogs gay.', False),
    )
    return FixMessage.from_pairs(pairs)



@pytest.fixture
async def session(engine, test_server, client_config):
    host = test_server.config['host']
    port = test_server.config['port']
    async with engine.connect(host, port, client_config) as session:
        yield session


@pytest.mark.asyncio
async def test_can_login_logout(session, client_config):
    await session.logon()
    msg = await session.receive(timeout=0.1)
    assert msg.msg_type == fix.FixMsgType.LOGON
    assert msg.get(56) == client_config['sender_comp_id']

    await session.logout()
    msg = await session.receive(timeout=0.1)
    assert msg.msg_type == fix.FixMsgType.LOGOUT



@pytest.mark.asyncio
async def test_can_iterate(session, test_request):
    await session.logon()
    async for msg in session:
        assert msg.msg_type == fix.FixMsgType.LOGON
        break

    session.send(test_request)
    await session.drain()
    async for msg in session:
        assert msg.msg_type == fix.FixMsgType.HEARTBEAT
        assert msg.get(fix.FixTag.TestReqID) == test_request.get(fix.FixTag.TestReqID)
        break


@pytest.mark.asyncio
async def test_receive_timeout(session):
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
@pytest.mark.parametrize('client_config', [{'heartbeat_interval': 1}], indirect=True)
@pytest.mark.asyncio
async def test_heartbeat(session):
    await session.logon()

    msg = await session.receive(timeout=0.1)
    assert msg.msg_type == fix.FixMsgType.LOGON
    msg = await session.receive(timeout=1.2)
    assert msg.msg_type == fix.FixMsgType.HEARTBEAT


@pytest.mark.parametrize('client_config', [{'heartbeat_interval': 90}], indirect=True)
@pytest.mark.asyncio
async def test_incorrect_heartbeat_int(session):
    await session.logon()
    msg = await session.receive(timeout=0.1)
    assert msg.msg_type == fix.FixMsgType.REJECT
    assert int(msg.get(fix.FixTag.RefTagID)) == fix.FixTag.HeartBtInt


@pytest.mark.parametrize('client_config', [{'target_comp_id': 'not-a-correct-id'}], indirect=True)
@pytest.mark.asyncio
async def test_incorrect_target_comp_id(session):
    await session.logon()
    with pytest.raises(ConnectionAbortedError):
        await session.receive(timeout=0.1)


@pytest.mark.parametrize('client_config', [{'sender_comp_id': 'not-a-correct-id'}], indirect=True)
@pytest.mark.asyncio
async def test_incorrect_sender_comp_id(session):
    await session.logon()
    with pytest.raises(ConnectionAbortedError):
        await session.receive(timeout=0.1)


@pytest.mark.asyncio
async def test_test_request(session, test_request):
    await session.logon()
    session.send(test_request)

    msg = await session.receive()
    assert msg.msg_type == fix.FixMsgType.LOGON

    msg = await session.receive()
    assert msg.msg_type == fix.FixMsgType.HEARTBEAT
    assert msg.get(fix.FixTag.TestReqID) == test_request.get(fix.FixTag.TestReqID)


@pytest.mark.asyncio
async def test_reset_seq_num(session, test_request):
    await session.logon()

    msg = await session.receive()
    assert msg.msg_type == fix.FixMsgType.LOGON

    await session.reset()

    async for msg in session:
        if msg.msg_type == fix.FixMsgType.LOGON:
            break

    assert msg.get(fix.FixTag.ResetSeqNumFlag) == fix.ResetSeqNumFlag.YES
    assert msg.seq_num == 1

    local_seq_num = await session.get_local_sequence()
    assert local_seq_num == 2
    remote_seq_num = await session.get_remote_sequence()
    assert remote_seq_num == 2

    stored = await session.history()
    assert len(stored) == 2

    session.send(test_request)
    await session.drain()
    msg = await session.receive()
    assert msg.msg_type == fix.FixMsgType.HEARTBEAT
    assert msg.get(fix.FixTag.TestReqID) == test_request.get(fix.FixTag.TestReqID)


@pytest.mark.asyncio
async def test_sequence_reset(session, test_server, test_request):
    await session.logon()

    msg = await session.receive()
    assert msg.msg_type == fix.FixMsgType.LOGON

    # TODO This is dumb, find a better way to test a hard
    # reset
    server_session = test_server.client_sessions[0]
    await server_session._set_local_sequence(9)
    sequence_reset = helpers.make_sequence_reset(10)
    server_session.send(sequence_reset)

    msg = await session.receive()
    assert msg.msg_type == fix.FixMsgType.SEQUENCE_RESET

    new_remote_seq_num = int(msg.get(fix.FixTag.NewSeqNo))
    assert new_remote_seq_num == await session.get_remote_sequence()

    session.send(test_request)
    msg = await session.receive()
    assert msg.msg_type == fix.FixMsgType.HEARTBEAT
    assert msg.get(fix.FixTag.TestReqID) == test_request.get(fix.FixTag.TestReqID)


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

            test_server.client_sessions[0].send(news_msg)
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

