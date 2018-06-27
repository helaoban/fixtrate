import asyncio
import pytest

from fixation import parse, constants


@pytest.mark.asyncio
async def test_login(
    fix_session,
    client_config,
    client_store,
):
    async with fix_session.connect():
        await fix_session.login()
        await asyncio.sleep(0.1)

    first_sent = client_store.get_sent_message_by_index(0)
    first_sent = parse.FixParser.parse(first_sent, client_config)
    msg_type = constants.FixMsgType(first_sent.get(
        constants.FixTag.MsgType))
    assert msg_type == constants.FixMsgType.MsgType_Logon

    first_received = client_store.get_received_message_by_index(0)
    first_received = parse.FixParser.parse(first_received, client_config)
    msg_type = constants.FixMsgType(first_received.get(
        constants.FixTag.MsgType))
    assert msg_type == constants.FixMsgType.MsgType_Logon

    server_sequence_number = int(first_received.get(
        constants.FixTag.MsgSeqNum))

    second_sent = client_store.get_sent_message_by_index(1)
    second_sent = parse.FixParser.parse(second_sent, client_config)
    msg_type = constants.FixMsgType(second_sent.get(
        constants.FixTag.MsgType))
    assert msg_type == constants.FixMsgType.MsgType_Heartbeat

    assert int(fix_session.store.get_remote_sequence_number()) == server_sequence_number


@pytest.mark.asyncio
async def test_iterate_messages(fix_session):

    messages = []

    async def iter_messages():
        async with fix_session.connect():
            await fix_session.login()
            async for msg in fix_session:
                messages.append(msg)

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(iter_messages(), timeout=2)

    assert len(messages) > 0


@pytest.mark.asyncio
async def test_heartbeat(fix_session, test_server, client_store, client_config):

    fix_session.config.heartbeat_interval = 1
    test_server.config.heartbeat_interval = 1
    messages = []

    async def iter_messages():
        async with fix_session.connect():
            await fix_session.login()
            async for msg in fix_session:
                messages.append(msg)

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(iter_messages(), timeout=2)

    received_heartbeats = [
        m for m in messages
        if constants.FixMsgType(m.message_type) == constants.FixMsgType.MsgType_Heartbeat
    ]

    assert len(received_heartbeats) > 0

    sent_messages = [
        parse.FixParser.parse(v, client_config)
        for k, v in client_store.get_sent_messages()
    ]

    sent_heartbeats = [
        m for m in sent_messages
        if constants.FixMsgType(m.message_type) == constants.FixMsgType.MsgType_Heartbeat
    ]

    assert len(sent_heartbeats) > 0


@pytest.mark.asyncio
async def test_test_request(fix_session):

    messages = []

    async def iter_messages():
        async with fix_session.connect():
            await fix_session.login()
            await fix_session.send_test_request()
            async for msg in fix_session:
                messages.append(msg)

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(iter_messages(), timeout=2)

    heartbeats = [
        m for m in messages
        if constants.FixMsgType(m.message_type) == constants.FixMsgType.MsgType_Heartbeat
    ]

    test_request_id = heartbeats[0].get(constants.FixTag.TestReqID)
    assert test_request_id is not None
