import asyncio
import pytest
import uuid

from fixtrate import constants as fix
from fixtrate.message import FixMessage

TAGS = fix.FixTag.FIX42


@pytest.mark.asyncio
async def test_successful_login(fix_session, test_server):
    async with fix_session.connect():
        await fix_session.logon()
        async for msg in fix_session:
            assert msg.msg_type == fix.FixMsgType.LOGON
            break
        else:
            raise AssertionError('No message received')


@pytest.mark.asyncio
async def test_receive(fix_session, test_server):

    async with fix_session.connect():
        await fix_session.logon()

        msg = await fix_session.receive()
        assert msg.msg_type == fix.FixMsgType.LOGON

        with pytest.raises(asyncio.TimeoutError):
            msg = await fix_session.receive(timeout=0.1)


@pytest.mark.asyncio
async def test_heartbeat(fix_session, test_server):

    fix_session.config['heartbeat_interval'] = 1
    test_server.update_session_conf({
        'heartbeat_interval': 1
    })

    async with fix_session.connect():
        await fix_session.logon()

        msg = await fix_session.receive()
        assert msg.msg_type == fix.FixMsgType.LOGON

        msg = await fix_session.receive()
        assert msg.msg_type == fix.FixMsgType.HEARTBEAT


@pytest.mark.asyncio
async def test_incorrect_heartbeat_int(fix_session, test_server):
    fix_session.config['heartbeat_interval'] = 90

    async with fix_session.connect():
        await fix_session.logon()
        msg = await fix_session.receive()
        assert msg.msg_type == fix.FixMsgType.REJECT


@pytest.mark.asyncio
async def test_incorrect_target_comp_id(fix_session, test_server):
    fix_session.config['target_comp_id'] = 'not-a-correct-id'

    async with fix_session.connect():
        await fix_session.logon()
        msg = await fix_session.receive()
        assert msg.msg_type == fix.FixMsgType.REJECT


@pytest.mark.asyncio
async def test_reset_seq_num(fix_session, test_server):

    test_id = str(uuid.uuid4())

    async with fix_session.connect():
        await fix_session.logon()

        msg = await fix_session.receive()
        assert msg.msg_type == fix.FixMsgType.LOGON

        await fix_session._send_test_request(test_id)
        msg = await fix_session.receive()
        assert msg.msg_type == fix.FixMsgType.HEARTBEAT
        assert msg.get(112) == test_id

        await fix_session.logon(reset=True)

        msg = await fix_session.receive()
        local_seq_num = await fix_session.get_local_sequence()

        assert msg.msg_type == fix.FixMsgType.LOGON
        assert msg.get(TAGS.ResetSeqNumFlag) == fix.ResetSeqNumFlag.YES
        assert msg.seq_num == 1
        assert local_seq_num == 2


@pytest.mark.asyncio
async def test_test_request(fix_session, test_server):

    test_id = str(uuid.uuid4())

    async with fix_session.connect():
        await fix_session.logon()
        await fix_session._send_test_request(test_id)

        msg = await fix_session.receive()
        assert msg.msg_type == fix.FixMsgType.LOGON

        msg = await fix_session.receive()
        assert msg.msg_type == fix.FixMsgType.HEARTBEAT
        assert msg.get(112) == test_id


@pytest.mark.asyncio
async def test_sequence_reset(fix_session, test_server):

    async with fix_session.connect():
        await fix_session.logon()

        msg = await fix_session.receive()
        assert msg.msg_type == fix.FixMsgType.LOGON

        client_sessions = list(test_server.client_sessions.values())

        pairs = (
            (TAGS.MsgType, fix.FixMsgType.SEQUENCE_RESET, True),
            (TAGS.PossDupFlag, 'Y', True),
            (TAGS.GapFillFlag, 'Y', False),
            (TAGS.NewSeqNo, 10, False),
        )
        seq_reset_msg = FixMessage.from_pairs(pairs)

        await client_sessions[0].send(seq_reset_msg)

        msg = await fix_session.receive()
        assert msg.msg_type == fix.FixMsgType.SEQUENCE_RESET

        new_seq_num = int(msg.get(36))
        current_seq_num = await fix_session.get_remote_sequence()
        assert current_seq_num == new_seq_num


@pytest.mark.asyncio
async def test_message_recovery(fix_session, test_server):

    fix_session.config['heartbeat_interval'] = 1
    test_server.update_session_conf({
        'heartbeat_interval': 1
    })

    async with fix_session.connect():
        await fix_session.logon()
        msg = await fix_session.receive()
        assert msg.msg_type == fix.FixMsgType.LOGON

    pairs = (
        (TAGS.MsgType, fix.FixMsgType.NEWS, True),
        (TAGS.Headline, 'BREAKING NEWS', False),
        (TAGS.LinesOfText, 1, False),
        (TAGS.Text, 'Government admits turning frogs gay.', False),
    )
    news_msg = FixMessage.from_pairs(pairs)

    server_sessions = list(test_server.client_sessions.values())
    await server_sessions[0].send(news_msg)

    async with fix_session.connect():
        await fix_session.logon()

        # the logon msg
        msg = await fix_session.receive()
        assert msg.msg_type == fix.FixMsgType.LOGON

        # the news msg
        msg = await fix_session.receive()
        assert msg.msg_type == fix.FixMsgType.NEWS

        # gap fill for the second logon msg
        msg = await fix_session.receive()
        assert msg.msg_type == fix.FixMsgType.SEQUENCE_RESET

        # # the next message should process fine
        msg = await fix_session.receive()
        assert msg.msg_type == fix.FixMsgType.HEARTBEAT
