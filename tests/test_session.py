import asyncio
import pytest
import uuid

from fixation import constants as fc

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
            assert fix_session._store.get_seq_num() == 2
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
async def test_recover_from_disconnect(fix_session, test_server):

    async with fix_session.connect():
        await fix_session.logon()
        async for msg in fix_session:
            assert msg.msg_type == fc.FixMsgType.Logon
            break
        else:
            raise AssertionError('No message received')

        test_server.close()
        await test_server.wait_close()

        # flush any remaning msgs from buffer
        async for msg in fix_session:
            pass

        test_server.start()

        async for msg in fix_session:
            assert msg.msg_type == fc.FixMsgType.Heartbeat
        else:
            raise AssertionError('No message received')
