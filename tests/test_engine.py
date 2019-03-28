import pytest
from fixtrate import constants as fix


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


