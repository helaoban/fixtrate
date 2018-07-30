import asyncio
import pytest
import uuid


from async_timeout import timeout

from fixation import constants as fc, message as fm

TAGS = fc.FixTag.FIX42


@pytest.mark.asyncio
async def test_with_context_manager(fix_session, test_server):

    await fix_session.connect()
    await fix_session.logon()
    msg = await fix_session._recv_msg()
    assert msg.msg_type == fc.FixMsgType.Logon
    await fix_session.close()


@pytest.mark.asyncio
async def test_successful_login(fix_session, test_server):
    async with fix_session.connect():
        await fix_session.logon()
        async for msg in fix_session:
            assert msg.msg_type == fc.FixMsgType.Logon
            break
        else:
            raise AssertionError('No message received')


@pytest.mark.asyncio
async def test_heartbeat(fix_session, test_server):

    fix_session._config['HEARTBEAT_INTERVAL'] = 1
    test_server.config['HEARTBEAT_INTERVAL'] = 1

    async with fix_session.connect():
        await fix_session.logon()

        msg = await fix_session._recv_msg()
        assert msg.msg_type == fc.FixMsgType.Logon

        msg = await fix_session._recv_msg()
        assert msg.msg_type == fc.FixMsgType.Heartbeat


@pytest.mark.asyncio
async def test_incorrect_heartbeat_int(fix_session, test_server):
    fix_session._config['FIX_HEARTBEAT_INTERVAL'] = 90
    async with fix_session.connect():
        await fix_session.logon()
        async for msg in fix_session:
            assert msg.msg_type == fc.FixMsgType.Reject
            break
        else:
            raise AssertionError('No message received')


@pytest.mark.asyncio
async def test_incorrect_target_comp_id(fix_session, test_server):
    fix_session._config['FIX_TARGET_COMP_ID'] = 'not-a-correct-id'
    async with fix_session.connect():
        await fix_session.logon()
        async for msg in fix_session:
            assert msg.msg_type == fc.FixMsgType.Reject
            break
        else:
            raise AssertionError('No message received')


@pytest.mark.asyncio
async def test_new_seq_num(fix_session, test_server):

    test_id = str(uuid.uuid4())

    async with fix_session.connect():
        await fix_session.logon()
        async for msg in fix_session:
            assert msg.msg_type == fc.FixMsgType.Logon
            break
        else:
            AssertionError('No message received')

        await fix_session._send_test_request(test_id)
        async for msg in fix_session:
            if msg.msg_type == fc.FixMsgType.Heartbeat:
                if msg.get(112) == test_id:
                    break
        else:
            raise AssertionError('No message received')

        await fix_session.logon(reset=True)
        async for msg in fix_session:
            assert msg.msg_type == fc.FixMsgType.Logon
            assert msg.get(TAGS.ResetSeqNumFlag) == fc.ResetSeqNumFlag.YES
            assert msg.seq_num == 1
            stored_seq_num = await fix_session._store.get_seq_num()
            assert stored_seq_num == 2
            break
        else:
            raise AssertionError('No message received')


@pytest.mark.asyncio
async def test_test_request(fix_session, test_server):

    test_id = str(uuid.uuid4())

    async with fix_session.connect():
        await fix_session.logon()
        await fix_session._send_test_request(test_id)
        async for msg in fix_session:
            if msg.msg_type == fc.FixMsgType.Heartbeat:
                if msg.get(112) == test_id:
                    break
        else:
            raise AssertionError('No message received')


@pytest.mark.asyncio
async def test_message_recovery(fix_session, test_server):

    async with fix_session.connect():
        await fix_session.logon()
        async for msg in fix_session:
            assert msg.msg_type == fc.FixMsgType.Logon
            break
        else:
            raise AssertionError('No message received')

    pairs = (
        (TAGS.MsgType, fc.FixMsgType.News, True),
        (TAGS.Headline, 'BREAKING NEWS', False),
        (TAGS.LinesOfText, 1, False),
        (TAGS.Text, 'Government admits turning frogs gay.', False),
    )
    news_msg = fm.FixMessage.from_pairs(pairs)

    client_sessions = list(test_server._clients.values())
    await client_sessions[0].send_message(news_msg)

    async with fix_session.connect():
        await fix_session.logon()
        async for msg in fix_session:
            assert msg.msg_type == fc.FixMsgType.Logon
            break
        else:
            raise AssertionError('No message received')

        # the news msg
        msg = await fix_session._recv_msg()
        assert msg.msg_type == fc.FixMsgType.News

        # gap fill for the second logon msg
        msg = await fix_session._recv_msg()
        assert msg.msg_type == fc.FixMsgType.SequenceReset

        # there should be no more messages
        msg = None
        try:
            async with timeout(1):
                msg = await fix_session._recv_msg()
        except asyncio.TimeoutError:
            pass
        assert msg is None
