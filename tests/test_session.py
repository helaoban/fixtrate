import asyncio as aio
import pytest  # type: ignore
import typing as t
import uuid

from fixtrate import helpers
from fixtrate.message import FixMessage
from fixtrate.session import FixSession
from fixtrate.peer import connect as fix_connect
from fixtrate.fixt import data as VALUES
from fixtrate.fix42.types import FixTag as TAGS
from .conftest import MockFixServer

MTYPE = VALUES.MsgType


def make_test_request():
    id_ = str(uuid.uuid4())
    return helpers.make_test_request_msg(id_)


@pytest.fixture
def news_msg() -> FixMessage:
    pairs = (
        (TAGS.MsgType, MTYPE.NEWS, True),
        (TAGS.Headline, 'BREAKING NEWS', False),
        (TAGS.LinesOfText, 1, False),
        (TAGS.Text, 'Government admits turning frogs gay.', False),
    )
    return FixMessage.from_pairs(pairs)


@pytest.fixture
async def session(
    test_server: MockFixServer,
    client_dsn: str,
    store_dsn: str,
) -> t.AsyncIterator[FixSession]:
    async with fix_connect(client_dsn, store_dsn=store_dsn) as session:
        yield session


@pytest.mark.asyncio
@pytest.mark.timeout(3)
async def test_can_login_logout(
    test_server: MockFixServer,
    client_dsn: str,
    store_dsn: str,
) -> None:
    session = await fix_connect(client_dsn, store_dsn=store_dsn)
    msg = await session.receive(timeout=0.1)
    assert msg.msg_type == MTYPE.LOGON
    assert msg.get_raw(56) == "TESTCLIENT"
    await session.logout()
    msg = await session.receive(timeout=0.1)
    assert msg.msg_type == MTYPE.LOGOUT
    await session.close()


@pytest.mark.asyncio
@pytest.mark.timeout(3)
async def test_can_iterate(session: FixSession) -> None:
    test_msg = make_test_request()

    await session.send(test_msg)

    msgs: t.List[FixMessage] = []
    async for msg in session:
        msgs.append(msg)
        if len(msgs) == 2:
            break

    assert msgs[0].msg_type == MTYPE.LOGON
    assert msgs[1].msg_type == MTYPE.HEARTBEAT
    assert msgs[1].get_raw(TAGS.TestReqID) == test_msg.get_raw(TAGS.TestReqID)


@pytest.mark.asyncio
@pytest.mark.timeout(3)
async def test_receive_timeout(session: FixSession) -> None:
    msg = await session.receive()
    assert msg.msg_type == MTYPE.LOGON
    with pytest.raises(aio.TimeoutError):
        await session.receive(timeout=0.1)


@pytest.mark.parametrize("hb_int", [1], indirect=True)
@pytest.mark.asyncio
@pytest.mark.timeout(3)
async def test_heartbeat(
    hb_int: int,
    client_dsn: str,
    session: FixSession,
) -> None:
    msg = await session.receive(timeout=0.1)
    assert msg.msg_type == MTYPE.LOGON
    msg = await session.receive(timeout=1.2)
    assert msg.msg_type == MTYPE.HEARTBEAT


@pytest.mark.parametrize(
    "client_dsn",
    ["fix://TESTCLIENT:TESTSERVER@127.0.0.1:8686/?hb_int=90"],
    indirect=True
)
@pytest.mark.asyncio
@pytest.mark.timeout(3)
async def test_bad_hb_int(session: FixSession) -> None:
    msg = await session.receive(timeout=0.1)
    assert msg.msg_type == MTYPE.REJECT
    assert msg.get_raw(TAGS.RefTagID) == TAGS.HeartBtInt


@pytest.mark.asyncio
@pytest.mark.timeout(3)
async def test_test_request(session: FixSession) -> None:
    test_msg = make_test_request()
    await session.send(test_msg)

    logon_msg = await session.receive()
    assert logon_msg.msg_type == MTYPE.LOGON

    hb_msg = await session.receive()
    assert hb_msg.msg_type == MTYPE.HEARTBEAT
    assert hb_msg.get_raw(TAGS.TestReqID) == test_msg.get_raw(TAGS.TestReqID)


@pytest.mark.asyncio
@pytest.mark.timeout(3)
async def test_reset_seq_num(
    session: FixSession,
    test_server: MockFixServer,
) -> None:

    logon_msg = await session.receive()
    assert logon_msg.msg_type == MTYPE.LOGON

    await session.reset()
    logon_reset_msg = await session.receive()
    assert logon_reset_msg.msg_type == MTYPE.LOGON
    assert logon_reset_msg.get_raw(TAGS.ResetSeqNumFlag) == "Y"
    assert logon_reset_msg.seq_num == 1

    # assert that after the reset, both local and
    # remote sequence numbers should be 2, for both
    # peers
    assert await session._store.get_local() == 1
    assert await session._store.get_remote() == 2

    server_session = test_server.sessions[0]
    assert await server_session._store.get_local() == 1
    assert await server_session._store.get_remote() == 2

    # Just after the reset, we should only have 2
    # messages in the store, the outgoing and responding
    # logon messages
    stored_msgs = []
    async for m in session.history():
        assert m.msg_type == MTYPE.LOGON
        stored_msgs.append(m)
    assert len(stored_msgs) == 2

    stored_msgs = []
    async for m in server_session.history():
        assert m.msg_type == MTYPE.LOGON
        stored_msgs.append(m)
    assert len(stored_msgs) == 2

    # send a test request to make sure
    # the session can now proceed as normal
    test_req_id = str(uuid.uuid4())
    await session.test(test_req_id)
    hb_msg = await session.receive()
    assert hb_msg.msg_type == MTYPE.HEARTBEAT
    assert hb_msg.get_raw(TAGS.TestReqID) == test_req_id


@pytest.mark.asyncio
@pytest.mark.timeout(3)
async def test_seq_reset(
    session: FixSession,
    test_server: MockFixServer,
) -> None:

    logon_msg = await session.receive()
    assert logon_msg.msg_type == MTYPE.LOGON

    # Artifically set the server local sequence
    # number to 9, so seq num of the sequence reset
    # message sent below will be 10.
    server_session = test_server.sessions[0]
    await server_session._store.set_local(8)

    # The server sends a sequence reset message,
    # informing the peer that the next sequence number
    # will be 10
    sequence_reset = helpers.make_sequence_reset(10)
    await server_session.send(sequence_reset)

    # send a test request to make sure we are back
    # in sequence and message processing is
    # proceeding as normal.
    test_req_id = str(uuid.uuid4())
    await session.test(test_req_id)
    hb_msg = await session.receive()
    assert hb_msg.msg_type == MTYPE.HEARTBEAT
    assert hb_msg.get_raw(TAGS.TestReqID) == test_req_id
    assert hb_msg.seq_num == 10
    assert await session._store.get_remote() == 11


@pytest.mark.parametrize("hb_int", [1], indirect=True)
@pytest.mark.asyncio
@pytest.mark.timeout(3)
async def test_msg_recovery(
    test_server: MockFixServer,
    hb_int: int,
    client_dsn: str,
    store_dsn: str,
    news_msg: FixMessage,
) -> None:
    # In this test we simulate a connection
    # interruption where a peer sends a message
    # (and records the sent message) but the other peer
    # fails to receive the message.

    # Here we send a message from the 'server'
    # but raise an exceptions before the message
    # can hit the wire.
    with pytest.raises(ConnectionAbortedError):
        async with fix_connect(client_dsn, store_dsn=store_dsn) as session:
            msg = await session.receive()
            assert msg.msg_type == MTYPE.LOGON

            client_session = test_server.sessions[0]
            await client_session.send(news_msg)
            raise ConnectionAbortedError

    # After reconnection to session, we test that we
    # correctly receive the news message, a gap fill
    # message for the logon message that came in out-of-sequence,
    # and finally a heartbeat message which is the first message
    # after the resent messages.

    async with fix_connect(client_dsn, store_dsn=store_dsn) as session:
        # the news msg
        msg = await session.receive(skip_duplicate=False)
        assert msg.msg_type == MTYPE.NEWS

        # gap fill for the second logon msg
        msg = await session.receive(skip_duplicate=False)
        assert msg.msg_type == MTYPE.SEQUENCE_RESET

        # the next message should process fine
        msg = await session.receive(timeout=2)
        assert msg.msg_type == MTYPE.HEARTBEAT
