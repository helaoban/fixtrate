import asyncio
import pytest
import uuid

from fixation import constants as fc, message as fm

TAGS = fc.FixTag.FIX42


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

    async def iter_messages():
        async with fix_session.connect():
            await fix_session.logon()
            async for msg in fix_session:
                assert msg.msg_type == fc.FixMsgType.Logon
                break
            else:
                raise AssertionError('No message received')

            async for msg in fix_session:
                assert msg.msg_type == fc.FixMsgType.Heartbeat
                break
            else:
                raise AssertionError('No message received')

    await asyncio.wait_for(iter_messages(), timeout=2)


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

    news_msg = fm.FixMessage()
    news_msg.append_pair(
        TAGS.MsgType,
        fc.FixMsgType.News,
        header=True
    )
    news_msg.append_pair(TAGS.Headline, 'BREAKING NEWS')
    news_msg.append_pair(TAGS.LinesOfText, 1)
    news_msg.append_pair(TAGS.Text, 'Government admits turning frogs gay.')

    _, server_session = test_server._clients[0]
    await server_session.send_message(news_msg)

    async with fix_session.connect():
        await fix_session.logon()
        async for msg in fix_session:
            assert msg.msg_type == fc.FixMsgType.Logon
            break
        else:
            raise AssertionError('No message received')

        async for msg in fix_session:
            assert msg.msg_type == fc.FixMsgType.News
            assert msg.is_duplicate
            break
        else:
            raise AssertionError('No message received')