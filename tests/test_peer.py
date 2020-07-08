import pytest  # type: ignore
import contextlib
from fix.peer import connect as fix_connect, parse_conn_args
from fix.fixt.data import MsgType as MT


@pytest.mark.asyncio
async def test_auto_logs_out(test_server, client_dsn):
    async with fix_connect(client_dsn) as session:
        msg = await session.receive()
        assert msg.msg_type == MT.LOGON
        assert msg.get_raw(56) == "TESTCLIENT"

    assert not session.logged_on


def test_parse_fix_config():
    dsn = "fix+4.2://qafa001:IB@127.0.0.1:31831/?account=U3281&qualifier=ib1"

    config = parse_conn_args(dsn)
    assert config.version == "FIX.4.2"
    assert config.sender == "qafa001"
    assert config.target == "IB"
    assert config.qualifier == "ib1"
    assert config.host == "127.0.0.1"
    assert config.port == 31831
    assert config.hb_int == 30
    assert config.account == "U3281"

    config = parse_conn_args(
        version="4.2",
        sender="qafa001",
        target="IB",
        host="127.0.0.1",
        port=31831,
        account="U3281",
        qualifier="ib1",
    )
    assert config.version == "FIX.4.2"
    assert config.sender == "qafa001"
    assert config.target == "IB"
    assert config.qualifier == "ib1"
    assert config.host == "127.0.0.1"
    assert config.port == 31831
    assert config.hb_int == 30
    assert config.account == "U3281"


@pytest.mark.asyncio
async def test_blocks_dup_conn(
    test_server, client_dsn, store_dsn
):
    async with contextlib.AsyncExitStack() as stack:

        session1 = await stack.enter_async_context(
            fix_connect(client_dsn, store_dsn=store_dsn))
        _ = await session1.receive()

        session2 = await stack.enter_async_context(
            fix_connect(client_dsn, store_dsn=store_dsn))

        with pytest.raises(ConnectionAbortedError):
            _ = await session2.receive()
