import asyncio as aio
from datetime import datetime
import logging
import uuid
import time
import typing as t

from . import helpers, exceptions as exc
from .helpers import get_or_raise
from .parse import FixParser
from .fixt import data as VALUES
from .fixt.types import FixTag as TAGS


if t.TYPE_CHECKING:
    from .store.base import FixStore
    from .transport import Transport
    from .message import FixMessage
    from .config import FixSessionConfig
    SendHandler = t.Callable[[FixMessage], t.Any]


__all__ = ("FixSession", )


logger = logging.getLogger(__name__)


MTYPE = VALUES.MsgType
BAD_VAL = VALUES.SessionRejectReason.VALUE_IS_INCORRECT
INVALID_SEQ_RESET = (
    "SeqReset<4> attempting to decrease next "
    "expected sequence number. Current expected "
    "sequence number is %s, but SeqReset<4> is "
    "attempting to set the next expected sequence "
    "number to %s, this is now allowed."
)

FLAG_DEFAULT = 1 << 0
FLAG_WAIT_RESEND = 1 << 1
FLAG_WAIT_LOGOUT = 1 << 2
FLAG_LOGOUT_RESEND = 1 << 3
FLAG_INIT_LOGON = 1 << 4
FLAG_LOGGED_ON = 1 << 5
FLAG_CLOSED = 1 << 6
FLAG_CLOSING = 1 << 7


class FixSessionState:

    __slots__ = ("_state", )

    def __init__(self):
        self._state = FLAG_DEFAULT

    def set(self, flag: int) -> None:
        self._state = self._state | flag

    def unset(self, flag: int) -> None:
        self._state = self._state & ~flag

    def toggle(self, flag: int) -> None:
        self._state = self._state ^ flag

    def isset(self, flag: int) -> bool:
        return bool(self._state & flag)


class FixSession:
    """
    FIX Session Manager

    :param config: Session configuration object
    :param transport: Session transport
    :param store: Session store
    """

    def __init__(
        self,
        config: "FixSessionConfig",
        store: "FixStore",
        transport: "Transport",
    ):
        self.config = config
        self._store = store
        self._transport = transport
        self._hb_int = self.config.hb_int
        self._parser = FixParser()
        self._reset_request: t.Optional["FixMessage"] = None
        self._state = FixSessionState()
        self._lock = aio.Lock()
        self._gen: t.Optional[t.AsyncIterator["FixMessage"]] = None
        self._heartbeat_at = time.time() + self._hb_int
        self._outq: aio.Queue["FixMessage"] = aio.Queue()
        self.on_close: t.Optional[t.Callable] = None

        self.on_send: "t.Optional[SendHandler]" = None

    def __aiter__(self) -> t.AsyncIterator["FixMessage"]:
        return self

    async def __anext__(self) -> "FixMessage":
        return await self.receive()

    @property
    def id(self) -> t.Tuple[str, str, str, t.Optional[str]]:
        return (
            self.config.version,
            self.config.sender,
            self.config.target,
            self.config.qualifier,
        )

    @property
    def logged_on(self) -> bool:
        return self._state.isset(FLAG_LOGGED_ON)

    @property
    def closed(self) -> bool:
        """ Returns True if underlying connection
        is closing or has been closed.

        :return: bool
        """
        if self._state.isset(FLAG_CLOSING):
            return True
        if self._state.isset(FLAG_CLOSED):
            return True
        return False

    def history(self, *args, **kwargs) -> t.AsyncIterator["FixMessage"]:
        """ Return all messages sent and received in the
        current session.

        :rtype AsyncIterator[:class:`~fix.message.FixMessage`]
        """
        return self._store.get_msgs(*args, **kwargs)

    async def logon(self) -> None:
        """ Logon to a FIX Session. Sends a Logon<A> message to peer.
        """
        login_msg = helpers.make_logon_msg(hb_int=self._hb_int)
        await self.send(login_msg)

    async def test(self, test_req_id: t.Optional[str] = None) -> None:
        if test_req_id is None:
            test_req_id = str(uuid.uuid4())
        test_request_msg = helpers.make_test_request_msg(test_req_id)
        await self.send(test_request_msg)

    async def reset(self) -> None:
        login_msg = helpers.make_logon_msg(
            hb_int=self._hb_int, reset=True)
        login_msg.append_pair(57, str(uuid.uuid4()), header=True)
        self._reset_request = login_msg
        await self._send(login_msg, incr=False)

    async def logout(self) -> None:
        """
        Logout from a FIX Session.
        Sends a Logout<5> message to peer.
        """
        self._state.set(FLAG_WAIT_LOGOUT)
        await self.send(helpers.make_logout_msg())

    async def close(self) -> None:
        """
        Close the session. Closes the underlying connection and performs
        cleanup work.
        """
        if self.closed:
            return
        self._state.set(FLAG_CLOSING)
        if self._state.isset(FLAG_LOGGED_ON):
            logger.warning(
                f"Peer {self.config.sender} closed the connection "
                "without sending a logout message"
            )
        await self._transport.close()
        async with self._lock:
            await self._store.close()
        self._state.set(FLAG_CLOSED)

        if self.on_close is not None:
            self.on_close()

    async def send(self, msg: "FixMessage") -> None:
        """
        Send a FIX message to peer.

        :param msg: message to send.
        :type msg: :class:`~fix.message.FixMessage`
        """
        if self.closed:
            raise exc.SessionClosedError
        await self._send(msg)

    async def receive(
        self,
        timeout: t.Optional[float] = None,
        skip_admin: bool = False,
        skip_duplicate: bool = True,
    ) -> "FixMessage":
        gen = await self._get_gen()
        while True:
            try:
                msg = await aio.wait_for(gen.__anext__(), timeout)
            except aio.TimeoutError:
                self._gen = None
                raise
            if helpers.is_admin(msg) and skip_admin:
                continue
            if msg.is_duplicate and skip_duplicate:
                continue
            return msg

    async def _send(self, msg: "FixMessage", incr: bool = True) -> None:
        if msg.msg_type == MTYPE.LOGON:
            if self._state.isset(FLAG_INIT_LOGON):
                raise exc.FixError(
                    "Logon attempted while stil waiting for reply "
                    "to previous logon attempt"
                )
            if not self._state.isset(FLAG_LOGGED_ON):
                self._state.set(FLAG_INIT_LOGON)

        async with self._lock:
            await self._set_header(msg)
            await self._store.store_msg(msg)
            if incr:
                await self._store.incr_local()
            self._outq.put_nowait(msg)

    async def _drain(self) -> None:
        while True:
            try:
                msg = self._outq.get_nowait()
            except aio.QueueEmpty:
                break
            await self._transport.write(msg.encode())
            self._reset_hb()
            if self.on_send:
                self.on_send(msg)

    async def _set_header(self, msg: "FixMessage") -> None:
        if msg.get_raw(TAGS.MsgSeqNum) is None:
            seq_num = await self._store.get_local() + 1
            msg.append_pair(TAGS.MsgSeqNum, seq_num)

        msg.append_pair(TAGS.BeginString, self.config.version)
        msg.append_pair(TAGS.SenderCompID, self.config.sender)
        msg.append_pair(TAGS.TargetCompID, self.config.target)

        send_time = msg.get_raw(TAGS.SendingTime)
        if send_time is None:
            stamp = datetime.utcnow()
            msg.append_utc_timestamp(
                TAGS.SendingTime,
                timestamp=stamp,
                precision=6,
                header=True
            )

    async def _send_hb(self) -> None:
        if time.time() > self._heartbeat_at:
            await self.send(helpers.make_heartbeat_msg())

    def _reset_hb(self) -> None:
        self._heartbeat_at = time.time() + self._hb_int

    async def _validate_msg(self, msg: "FixMessage") -> None:
        """
        Do basic validation of message to make sure key tags
        are set and have the correct values.
        """
        helpers.validate_header(msg, self.config)

        if msg.msg_type == MTYPE.LOGON:
            hb_int = int(get_or_raise(msg, TAGS.HeartBtInt))
            if hb_int != self._hb_int:
                raise exc.IncorrectTagValueError(
                    msg, TAGS.HeartBtInt, self._hb_int, hb_int)

        try:
            hasattr(msg, "seq_num")
        except ValueError:
            raise exc.SessionError(
                f"Fatal error: Message {msg} does not "
                "have a sequence number set"
            )

    async def _poll(self) -> t.AsyncIterator["FixMessage"]:
        while True:
            if self.closed:
                raise exc.SessionClosedError
            await self._send_hb()
            await self._drain()
            msg = self._parser.get_message()
            if msg is not None:
                yield msg
            try:
                data = await aio.wait_for(self._transport.read(), 0.01)
            except ConnectionError:
                await self.close()
                raise
            except aio.TimeoutError:
                continue
            self._parser.append_buffer(data)

    async def _iter_msgs(self) -> t.AsyncIterator["FixMessage"]:
        async for msg in self._poll():

            try:
                await self._validate_msg(msg)
            except exc.InvalidMessageError as error:
                reject_msg = helpers.make_reject_msg_from_error(error)
                await self.send(reject_msg)
                logger.warning(
                    f"Invalid message was received and rejected: {error}")
                continue
            except exc.SessionError:
                await self.close()
                raise

            expected = await self._store.get_remote()
            gap = msg.seq_num - expected

            if gap > 0:
                if not (
                    self._state.isset(FLAG_WAIT_RESEND)
                    or helpers.is_reset_mode(msg)
                ):
                    resend_request = helpers.make_resend_request(expected, 0)
                    await self.send(resend_request)
                    self._state.set(FLAG_WAIT_RESEND)
            elif gap < 0:
                if not (
                    helpers.is_reset_mode(msg)
                    or helpers.is_logon_reset(msg)
                ):
                    if not msg.is_duplicate:
                        raise exc.FatalSequenceGapError(gap)
            else:
                async with self._lock:
                    await self._store.store_msg(msg)
                    await self._store.incr_remote()

                waiting_resend = self._state.isset(FLAG_WAIT_RESEND)
                if waiting_resend and not msg.is_duplicate:
                    self._state.unset(FLAG_WAIT_RESEND)
                    if self._state.isset(FLAG_LOGOUT_RESEND):
                        await self.send(helpers.make_logout_msg())

            if msg.msg_type == MTYPE.LOGON:
                self._state.set(FLAG_LOGGED_ON)
                if helpers.is_reset(msg):
                    await self._store.reset()
                    if self._reset_request:
                        await self._store.store_msg(self._reset_request, msg)
                        self._reset_request = None
                    else:
                        await self._store.store_msg(msg)
                        await self._send(
                            helpers.make_logon_msg(self._hb_int, reset=True),
                            incr=False
                        )
                else:
                    if self._state.isset(FLAG_INIT_LOGON):
                        self._state.unset(FLAG_INIT_LOGON)
                    else:
                        reply = helpers.make_logon_msg(self._hb_int)
                        await self.send(reply)

            elif msg.msg_type == MTYPE.LOGOUT:
                if gap > 0:
                    self._state.set(FLAG_LOGOUT_RESEND)
                await self.send(helpers.make_logout_msg())
                self._state.toggle(FLAG_WAIT_LOGOUT)
                self._state.unset(FLAG_LOGGED_ON)

            elif msg.msg_type == MTYPE.TEST_REQUEST:
                test_request_id = msg.get_raw(TAGS.TestReqID)
                reply = helpers.make_heartbeat_msg(test_request_id)
                await self.send(reply)

            elif msg.msg_type == MTYPE.REJECT:
                reason = msg.get_raw(TAGS.Text)
                logger.warning(
                    f"Peer {self.config.target} rejected message: {reason}")

            elif msg.msg_type == MTYPE.RESEND_REQUEST:
                if self._state.isset(FLAG_WAIT_LOGOUT):
                    logger.warning(
                        "Received a Resend Request after sending a Logout")
                start = int(get_or_raise(msg, TAGS.BeginSeqNo))
                end = float(get_or_raise(msg, TAGS.EndSeqNo))
                end = float("infinity") if end == 0 else end
                async for msg in helpers.get_resend_msgs(
                    self._store, start, end
                ):
                    await self._send(msg, incr=False)

            elif msg.msg_type == MTYPE.SEQUENCE_RESET:
                new = int(get_or_raise(msg, TAGS.NewSeqNo))
                if new < expected:
                    err = INVALID_SEQ_RESET % (expected, new)
                    reject_msg = helpers.make_reject_msg(
                        ref_sequence_number=msg.seq_num,
                        ref_message_type=msg.msg_type,
                        ref_tag=TAGS.NewSeqNo,
                        rejection_type=BAD_VAL,
                        reject_reason=err
                    )
                    await self.send(reject_msg)
                    # TODO shouldn't we exit with a fatal error here?

                await self._store.set_remote(new)

            if not helpers.is_logon_reset(msg) and gap:
                continue

            yield msg

    async def _get_gen(self) -> t.AsyncIterator["FixMessage"]:
        if self._gen is None:
            self._gen = self._iter_msgs()
        return self._gen
