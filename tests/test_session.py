import asyncio
import pytest

from fixation import parse, constants as fc


@pytest.mark.asyncio
async def test_login(
    fix_session,
    client_config,
    client_store,
):

    msgs = []

    async with fix_session.connect():
        await fix_session.logon()
        async for msg in fix_session:
            msgs.append(msg)
            break

    first = msgs[0]
    msg_type = fc.FixMsgType(first.get(fc.FixTag.FIX42.MsgType))
    assert msg_type == fc.FixMsgType.Heartbeat


@pytest.mark.asyncio
async def test_iterate_messages(fix_session):

    msgs = []

    async def iter_messages():
        async with fix_session.connect():
            await fix_session.logon()
            async for msg in fix_session:
                msgs.append(msg)

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(iter_messages(), timeout=2)

    assert len(msgs) > 0


@pytest.mark.asyncio
async def test_heartbeat(fix_session, test_server, client_store, client_config):

    # fix_session.config['FIX_HEARTBEAT_INTERVAL'] = 1
    # test_server.config['FIX_HEARTBEAT_INTERVAL'] = 1
    messages = []

    async def iter_messages():
        async with fix_session.connect():
            await fix_session.logon()
            async for msg in fix_session:
                messages.append(msg)

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(iter_messages(), timeout=2)

    received_heartbeats = [
        m for m in messages
        if fc.FixMsgType(m.message_type.decode()) == fc.FixMsgType.Heartbeat
    ]

    assert len(received_heartbeats) > 0

    sent_messages = [
        parse.FixParser.parse(v, client_config)
        for k, v in client_store.get_sent_messages()
    ]

    sent_heartbeats = [
        m for m in sent_messages
        if fc.FixMsgType(m.message_type.decode()) == fc.FixMsgType.Heartbeat
    ]

    assert len(sent_heartbeats) > 0


@pytest.mark.asyncio
async def test_test_request(fix_session):

    messages = []

    async def iter_messages():
        async with fix_session.connect():
            await fix_session.logon()
            await fix_session.send_test_request()
            async for msg in fix_session:
                messages.append(msg)

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(iter_messages(), timeout=2)

    heartbeats = [
        m for m in messages
        if fc.FixMsgType(m.message_type.decode()) == fc.FixMsgType.Heartbeat
    ]

    # test_request_id = heartbeats[0].get(fc.FixTag.FIX42.TestReqID)
    # assert test_request_id is not None
