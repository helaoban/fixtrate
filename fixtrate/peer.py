import asyncio as aio
import logging
import typing as t

from .utils import aio as aioutils
from .session import FixSession
from .transport import TCPTransport
from .server import FixServer, FixServerConfig
from .config import parse_conn_args, FixSessionConfig
from .store import create_store
from .fixt.data import MsgType as MTYPE


__all__ = ("connect", "bind")


logger = logging.getLogger(__name__)


async def _logout_session(session: FixSession):
    await session.logout()
    while True:
        msg = await session.receive()
        if msg.msg_type == MTYPE.LOGOUT:
            break


async def _connect(config: FixSessionConfig, store_dsn: str) -> FixSession:
    """
    Coroutine that waits for a successfuly connection to a FIX peer.
    Returns a FixConnection object. Can also be used as an async context
    manager, in which case the connection is automatically closed on
    exiting the context manager.

    :param address: tuple of (ip, port)
    :return: :class:`FixConnection` object
    :rtype: FixConnection
    """
    logger.debug(
        "Connecting to peer at "
        f"tcp://{config.host}:{config.port}"
    )
    store = await create_store(config, store_dsn)
    transport = await TCPTransport.connect(config.host, config.port)
    session = FixSession(
        config=config,
        store=store,
        transport=transport,
    )
    await session.logon()
    return session


async def on_session_exit(
    session: FixSession,
    exc_type,
    exc,
    tb,
) -> t.Optional[bool]:
    if isinstance(exc, ConnectionError):
        await session.close()
        return False
    else:
        try:
            await aio.wait_for(_logout_session(session), 2)
        except ConnectionError:
            logger.warning(
                "Connection error while attempting to logout")
        except aio.TimeoutError:
            logger.warning(
                "Timed-out while attempting to logout")
        except Exception as error:
            logger.warning(
                "Connection error while attempting to logout")
            logger.exception(error)
        await session.close()

    return None


def connect(
    dsn: t.Optional[str] = None,
    version: t.Optional[str] = None,
    host: t.Optional[str] = None,
    port: t.Optional[int] = None,
    sender: t.Optional[str] = None,
    target: t.Optional[str] = None,
    hb_int: t.Optional[int] = None,
    qualifier: t.Optional[str] = None,
    account: t.Optional[str] = None,
    store_dsn: str = "inmemory://",
) -> aioutils.AwaitableContextManager["FixSession"]:
    config = parse_conn_args(
        dsn=dsn,
        version=version,
        host=host,
        port=port,
        sender=sender,
        target=target,
        hb_int=hb_int,
        qualifier=qualifier,
        account=account,
    )
    return aioutils.AwaitableContextManager(
        _connect(config, store_dsn),
        on_exit=on_session_exit
    )


async def _bind(
    host: str,
    port: int,
    clients: t.Iterable[str],
    store: str = "inmemory://",
) -> FixServer:
    client_configs = []
    for client_dsn in clients:
        client_config = parse_conn_args(client_dsn)
        client_configs.append(client_config)
    config = FixServerConfig(host, port, store)
    server = FixServer(config, client_configs)
    await server.serve()
    return server


def bind(
    host: str,
    port: int,
    clients: t.Iterable[str],
    store: str = "inmemory://",
) -> aioutils.AwaitableContextManager["FixServer"]:
    return aioutils.AwaitableContextManager(
        _bind(host, port, clients, store),
    )
