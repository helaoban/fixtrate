import asyncio
import pytest
import uuid

from fixtrate import constants as fc, message as fm

TAGS = fc.FixTag.FIX42


@pytest.mark.asyncio
async def test_successful_login(fix_session, fix_endpoint, test_server):
    async with fix_session.connect(fix_endpoint):
        await fix_session.logon()
        async for msg in fix_session:
            assert msg.msg_type == fc.FixMsgType.LOGON
            break
        else:
            raise AssertionError('No message received')


@pytest.mark.asyncio
async def test_receive(fix_session, fix_endpoint, test_server):

    async with fix_session.connect(fix_endpoint):
        await fix_session.logon()

        msg = await fix_session.receive()
        assert msg.msg_type == fc.FixMsgType.LOGON

        with pytest.raises(asyncio.TimeoutError):
            msg = await fix_session.receive(timeout=2)

    fix_session._heartbeat_interval = 1
    test_server._heartbeat_interval = 1

    async with fix_session.connect(fix_endpoint):
        await fix_session.logon()

        msg = await fix_session.receive()
        assert msg.msg_type == fc.FixMsgType.LOGON

        msg = await fix_session.receive()
        assert msg.msg_type == fc.FixMsgType.HEARTBEAT


@pytest.mark.asyncio
async def test_heartbeat(fix_session, fix_endpoint, test_server):

    fix_session._heartbeat_interval = 1
    test_server._heartbeat_interval = 1

    async with fix_session.connect(fix_endpoint):
        await fix_session.logon()

        msg = await fix_session.receive()
        assert msg.msg_type == fc.FixMsgType.LOGON

        msg = await fix_session.receive()
        assert msg.msg_type == fc.FixMsgType.HEARTBEAT


@pytest.mark.asyncio
async def test_incorrect_heartbeat_int(fix_session, fix_endpoint, test_server):
    fix_session._heartbeat_interval = 90

    async with fix_session.connect(fix_endpoint):
        await fix_session.logon()
        msg = await fix_session.receive()
        assert msg.msg_type == fc.FixMsgType.REJECT


@pytest.mark.asyncio
async def test_incorrect_target_comp_id(fix_session, fix_endpoint, test_server):
    fix_session._target_comp_id = 'not-a-correct-id'

    async with fix_session.connect(fix_endpoint):
        await fix_session.logon()
        msg = await fix_session.receive()
        assert msg.msg_type == fc.FixMsgType.REJECT


@pytest.mark.asyncio
async def test_reset_seq_num(fix_session, fix_endpoint, test_server):

    test_id = str(uuid.uuid4())

    async with fix_session.connect(fix_endpoint):
        await fix_session.logon()

        msg = await fix_session.receive()
        assert msg.msg_type == fc.FixMsgType.LOGON

        await fix_session._send_test_request(test_id)
        msg = await fix_session.receive()
        assert msg.msg_type == fc.FixMsgType.HEARTBEAT
        assert msg.get(112) == test_id

        await fix_session.logon(reset=True)

        msg = await fix_session.receive()
        local_seq_num = await fix_session._store.get_seq_num()

        assert msg.msg_type == fc.FixMsgType.LOGON
        assert msg.get(TAGS.ResetSeqNumFlag) == fc.ResetSeqNumFlag.YES
        assert msg.seq_num == 1
        assert local_seq_num == 2


@pytest.mark.asyncio
async def test_test_request(fix_session, fix_endpoint, test_server):

    test_id = str(uuid.uuid4())

    async with fix_session.connect(fix_endpoint):
        await fix_session.logon()
        await fix_session._send_test_request(test_id)

        msg = await fix_session.receive()
        assert msg.msg_type == fc.FixMsgType.LOGON

        msg = await fix_session.receive()
        assert msg.msg_type == fc.FixMsgType.HEARTBEAT
        assert msg.get(112) == test_id


@pytest.mark.asyncio
async def test_sequence_reset(fix_session, fix_endpoint, test_server):

    async with fix_session.connect(fix_endpoint):
        await fix_session.logon()

        msg = await fix_session.receive()
        assert msg.msg_type == fc.FixMsgType.LOGON

        client_session = list(test_server._clients.values())[0]

        pairs = (
            (TAGS.MsgType, fc.FixMsgType.SEQUENCE_RESET, True),
            (TAGS.PossDupFlag, 'Y', True),
            (TAGS.GapFillFlag, 'Y', False),
            (TAGS.NewSeqNo, 10, False),
        )
        seq_reset_msg = fm.FixMessage.from_pairs(pairs)

        await client_session.send_message(seq_reset_msg)

        msg = await fix_session.receive()
        assert msg.msg_type == fc.FixMsgType.SEQUENCE_RESET

        new_seq_num = int(msg.get(36))
        current_seq_num = await fix_session._store.get_seq_num(remote=True)
        assert current_seq_num == new_seq_num


@pytest.mark.asyncio
async def test_message_recovery(fix_session, fix_endpoint, test_server):

    fix_session._heartbeat_interval = 1
    test_server._heartbeat_interval = 1

    async with fix_session.connect(fix_endpoint):
        await fix_session.logon()

        msg = await fix_session.receive()
        assert msg.msg_type == fc.FixMsgType.LOGON

    pairs = (
        (TAGS.MsgType, fc.FixMsgType.NEWS, True),
        (TAGS.Headline, 'BREAKING NEWS', False),
        (TAGS.LinesOfText, 1, False),
        (TAGS.Text, 'Government admits turning frogs gay.', False),
    )
    news_msg = fm.FixMessage.from_pairs(pairs)

    server_sessions = list(test_server._clients.values())
    await server_sessions[0].send_message(news_msg)

    async with fix_session.connect(fix_endpoint):
        await fix_session.logon()

        # the logon msg
        msg = await fix_session.receive()
        assert msg.msg_type == fc.FixMsgType.LOGON

        # the news msg
        msg = await fix_session.receive()
        assert msg.msg_type == fc.FixMsgType.NEWS

        # gap fill for the second logon msg
        msg = await fix_session.receive()
        assert msg.msg_type == fc.FixMsgType.SEQUENCE_RESET

        # the next message should process fine
        msg = await fix_session.receive()
        assert msg.msg_type == fc.FixMsgType.HEARTBEAT
