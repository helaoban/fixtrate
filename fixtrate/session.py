import asyncio
from collections.abc import Coroutine
import datetime as dt
import logging

import async_timeout

from . import constants as fc
from .exceptions import SequenceGap, FatalSequenceGap
from .factories import fix42
from .parse import FixParser
from .store import FixMemoryStore
from .signals import message_received, message_sent, sequence_gap
from .utils.aio import maybe_await
from .transport import TCPTransport, make_transport

logger = logging.getLogger(__name__)


ADMIN_MESSAGES = [
    fc.FixMsgType.LOGON,
    fc.FixMsgType.LOGOUT,
    fc.FixMsgType.HEARTBEAT,
    fc.FixMsgType.TEST_REQUEST,
    fc.FixMsgType.RESEND_REQUEST,
]

DEFAULT_TRANSPORT = TCPTransport

DEFAULT_OPTIONS = {
    'fix_version': fc.FixVersion.FIX42,
    'transport': None,
    'transport_options': {},
    'store': FixMemoryStore,
    'store_options': {},
    'heartbeat_interval': 30,
    'sender_comp_id': None,
    'target_comp_id': None,
    'host': None,
    'port': None,
    'receive_timeout': None,
    'fix_dict': None,
    'headers': []
}


def get_options(**kwargs):

    rv = dict(DEFAULT_OPTIONS)
    options = dict(**kwargs)

    for key, value in options.items():
        if key not in rv:
            raise TypeError("Unknown option %r" % (key,))
        rv[key] = value

    return rv


class FixSession:
    """
    FIX Session Manager

    :param sender_comp_id: Identifies the local peer. See
        http://fixwiki.org/fixwiki/SenderCompID
    :param target_comp_id: Identifies the remote peer See
        http://fixwiki.org/fixwiki/TargetCompID
    :param heartbeat_interval: How often (in seconds) to generate heartbeat
        messages during periods of inactivity. Default to 30.
    """

    def __init__(self, **kwargs):
        self.config = get_options(**kwargs)

        version = self.config.get('fix_version')
        self._tags = {
            'FIX.4.2': fc.FixTag.FIX42,
            'FIX.4.4': fc.FixTag.FIX44,
        }.get(version, fc.FixTag.FIX42)

        self.transport = make_transport(self.config)
        self.store = self._make_store()

        self._is_resetting = False
        self._hearbeat_cb = None

        self._waiting_resend = False
        self._waiting_logout_confirm = False
        self._logout_after_resend = False

        self.on_recv_msg_funcs = []
        self.on_send_msg_funcs = []

        self._initiator = None

        self.parser = FixParser()

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            msg = await self.receive()
        except (asyncio.TimeoutError, ConnectionError) as error:
            logger.error(error)
            raise StopAsyncIteration
        return msg

    def _make_store(self):
        store_cls = self.config['store']
        return store_cls(self.config['store_options'])

    async def get_initiator(self):
        if self._initiator is None:
            msgs = [m async for m in self.history(max=1)]
            if not msgs:
                return None
            first = msgs[0]
            self._initiator = first.get(49)
        return self._initiator

    @property
    def closed(self):
        """ Returns True if underlying connection
        is closing or has been closed.

        :return: bool
        """
        return self.transport.is_closing()

    def history(self, *args, **kwargs):
        """ Return all messages sent and received in the
        current session.

        :rtype AsyncIterator[:class:`~fixtrate.message.FixMessage`]
        """
        return self.store.get_messages(self, *args, **kwargs)

    async def get_local_sequence(self):
        """ Return the current local sequence number.

        :rtype int
        """
        return await self.store.get_local(self)

    async def get_remote_sequence(self):
        """ Return the current remote sequence number.

        :rtype int
        """
        return await self.store.get_remote(self)

    def connect(self):
        """
        Coroutine that waits for a successfuly connection to a FIX peer.
        Returns a FixConnection object. Can also be used as an async context
        manager, in which case the connection is automatically closed on
        exiting the context manager.

        :param address: tuple of (ip, port)
        :return: :class:`FixConnection` object
        :rtype: FixConnection
        """
        return _FixSessionContextManager(
            host=self.config['host'],
            port=self.config['port'],
            transport=self.transport,
            on_connect=self._on_connect,
            on_disconnect=self._on_disconnect,
        )

    async def logon(self, reset=False):
        """ Logon to a FIX Session. Sends a Logon<A> message to peer.

        :param reset: Whether to set ResetSeqNumFlag to 'Y' on the
            Logon<A> message.
        :type reset: bool
        """
        await self._send_login(reset)

    async def logoff(self):
        """ Logoff from a FIX Session. Sends a Logout<5> message to peer.
        """
        await self._send_logoff()

    async def close(self):
        """
        Close the session. Closes the underlying connection and performs
        cleanup work.
        """
        if self.closed:
            return
        logger.info('Shutting down...')
        await self._cancel_heartbeat_timer()
        await self.transport.close()
        await self.store.close(self)

    async def send(self, msg, skip_headers=False, **options):
        """
        Send a FIX message to peer.

        :param msg: message to send.
        :type msg: :class:`~fixtrate.message.FixMessage`
        :param bool skip_headers: (optional) If set to `True`, the session will
            not append the standard header before sending. Defaults to `False`
        """
        if not skip_headers:
            seq_num = await self.get_local_sequence()
            self._append_standard_header(msg, seq_num)

        if not msg.is_duplicate and not self._is_gap_fill(msg):
            await self._incr_local_sequence()

        await self._store_message(msg)

        for func in self.on_send_msg_funcs:
            await maybe_await(func, msg)

        message_sent.send(self, msg=msg)

        await self.transport.write(msg.encode(), **options)
        await self._reset_heartbeat_timer()

    def on_recv_message(self, f):
        """
        Decorator that registers a callback to be called when a message
        is received but before it has been processed by any session internal
        handlers.
        :param f: Callback function
        :return:
        """
        self.on_recv_msg_funcs.append(f)
        return f

    def on_send_message(self, f):
        """
        Decorator that registers a callback to be called when a message
        is about to be sent to peer.
        :param f:
        :return:
        """
        self.on_send_msg_funcs.append(f)
        return f

    async def _on_connect(self):
        await self.store.open(self)

    async def _on_disconnect(self):
        await self.close()

    async def _incr_local_sequence(self):
        return await self.store.incr_local(self)

    async def _incr_remote_sequence(self):
        return await self.store.incr_remote(self)

    async def _set_local_sequence(self, new_seq_num):
        return await self.store.set_local(self, new_seq_num)

    async def _set_remote_sequence(self, new_seq_num):
        return await self.store.set_remote(self, new_seq_num)

    async def _store_message(self, msg):
        await self.store.store_message(self, msg)

    def _append_standard_header(
        self,
        msg,
        seq_num,
        timestamp=None
    ):
        pairs = (
            (self._tags.BeginString, self.config.get('fix_version')),
            (self._tags.SenderCompID, self.config.get('sender_comp_id')),
            (self._tags.TargetCompID, self.config.get('target_comp_id')),
            (self._tags.MsgSeqNum, seq_num),
        )

        for tag, val in pairs:
            msg.append_pair(tag, val, header=True)

        timestamp = timestamp or dt.datetime.utcnow()
        msg.append_utc_timestamp(
            self._tags.SendingTime,
            timestamp=timestamp,
            precision=6,
            header=True
        )

        for tag, val in self.config.get('headers'):
            msg.append_pair(tag, val, header=True)

    async def _send_heartbeat(self, test_request_id=None):
        msg = fix42.heartbeat(test_request_id)
        await self.send(msg)

    async def _send_test_request(self, test_request_id):
        msg = fix42.test_request(test_request_id)
        await self.send(msg)

    async def _send_reject(self, msg, tag, rejection_type, reason):
        msg = fix42.reject(
            ref_sequence_number=msg.seq_num,
            ref_message_type=msg.msg_type,
            ref_tag=tag,
            rejection_type=rejection_type,
            reject_reason=reason,
        )
        await self.send(msg)

    async def _send_login(self, reset=False):
        login_msg = fix42.logon(
            heartbeat_interval=self.config.get('heartbeat_interval'),
            reset_sequence=reset
        )
        if reset:
            await self._set_local_sequence(1)
            self._append_standard_header(login_msg, seq_num=1)
            await self.send(login_msg, skip_headers=True)
        else:
            await self.send(login_msg)

    async def _send_logoff(self):
        if self._waiting_logout_confirm:
            # TODO what happends if Logout<5> sent twice?
            return
        logout_msg = fix42.logoff()
        await self.send(logout_msg)

    async def _request_resend(self, start, end):
        self._waiting_resend = True
        msg = fix42.resend_request(start, end)
        await self.send(msg)

    async def _reset_sequence(self, seq_num, new_seq_num):
        msg = fix42.sequence_reset(new_seq_num)
        self._append_standard_header(msg, seq_num)
        await self.send(msg, skip_headers=True)

    async def _resend_messages(self, start, end):
        """ Used internally by Fixtrate to handle the re-transmission of
        messages as a result of a Resend Request <2> message.

        The range of messages to be resent is requested from the
        store and iterated over. Each message is appended with a
        PossDupFlag tag set to 'Y' (Yes) and resent to the client,
        except for admin messages.

        Admin messages must not be resent. Contiguous sequences of
        admin messages are ignored, and a Sequence Reset <4> Gap Fill
        message is sent to instruct the client to increment the
        the next expected sequence number to the sequence number
        of the next non-admin message to be resent (represented by
        the value of NewSeqNo <36> in the Sequence Reset <4> message).

        For more information, see:
        https://www.onixs.biz/fix-dictionary/4.2/msgtype_2_2.html

        """
        # TODO support for end=0 must either be enforced here or in
        # the store!
        # TODO support for skipping the resend of certain business messages
        # based on config options (eg. stale order requests)

        gap_start = None
        gap_end = None

        async for msg in self.history(
                min=start, max=end, direction='sent'):

            if msg.msg_type in ADMIN_MESSAGES:
                if gap_start is None:
                    gap_start = msg.seq_num
                gap_end = msg.seq_num + 1
            else:
                if gap_end is not None:
                    await self._reset_sequence(gap_start, gap_end)
                    gap_start, gap_end = None, None
                msg.append_pair(
                    self._tags.PossDupFlag,
                    fc.PossDupFlag.YES,
                    header=True
                )
                await self.send(msg, skip_headers=True)

        if gap_start is not None:
            await self._reset_sequence(gap_start, gap_end)

    async def receive(self, timeout=None):
        """ Coroutine that waits for message from peer and returns it.

        :param timeout: (optional) timeout in seconds. If specified, method
            will raise asyncio.TimeoutError if message in not
            received after timeout. Defaults to `None`.
        :type timeout: float, int or None

        :return: :class:`~fixtrate.message.FixMessage` object
        """
        if timeout is None:
            timeout = self.config.get('receive_timeout')
        while True:
            msg = self.parser.get_message()
            if msg:
                break
            try:
                with async_timeout.timeout(timeout):
                    data = await self.transport.read()
            except (asyncio.CancelledError, asyncio.TimeoutError):
                raise asyncio.TimeoutError
            self.parser.append_buffer(data)

        if self.closed:
            raise ConnectionAbortedError
        if msg:
            await self._handle_message(msg)
        return msg

    async def _handle_message(self, msg):
        await self._store_message(msg)

        for func in self.on_recv_msg_funcs:
            await maybe_await(func, msg)

        message_received.send(self, msg=msg)

        try:
            await self._check_sequence_integrity(msg)
        except FatalSequenceGap:
            # a SeqReset<4>-Reset message should be processed
            # without deference to the MsgSeqNum
            if msg.msg_type == fc.FixMsgType.SEQUENCE_RESET:
                if not self._is_gap_fill(msg):
                    await self._handle_sequence_reset(msg)
                    return

            if msg.msg_type == fc.FixMsgType.LOGON:
                if self._is_reset(msg):
                    await self._handle_logon(msg)
                    return

            # Ignore message if gap < 0 and PossDupFlaf = 'Y'
            # TODO this is a unique event during message resend,
            # need to make sure we handle properly
            if msg.is_duplicate:
                return

            # This is an unrecoverable scenario, so we terminate
            # the session and raise the error.
            await self.close()
            raise
        except SequenceGap as error:
            sequence_gap.send(self, exc=error)

            # Always honor a ResendRequest<2> no matter what, even
            # if we are currently waiting on resend ourselves. This takes
            # care of an edge case that can occur when both sides detect a
            # sequence gap as a result of the respective Logon<A> messages.
            # If after detecting the gap the peer then sends both the
            # Logon<A> ack msg AND a ResendRequest<2> AT THE SAME TIME,
            # then the following scenario occurs:
            #   1. We process the Logon<4> msg, detect a gap, and immediately
            #      send a ResendRequest<2> (using 'through infinity' strat).
            #      This puts us into 'waiting on resend' mode, which causes us
            #      to ignore any out-of-sequence messages (where gap is > 0).
            #   2. We process the ResendRequest<@> sent by peer, which is also
            #      out-of-sequence (gap > 0) because we've had no time to
            #      process resent messages (at this point the peer has probably
            #      yet to receive our ResendRequest<2>). If we follow the
            #      'waiting-on-resend' rule, then we should ignore this out-of-
            #      -sequence msg and proceeed, but if we do that, the peer's
            #      ResendRequest<2> is not honored, and the FIX spec dictates
            #      that we must honor it, so we make an exception and proceed
            #      with message resend while disregarding the gap.
            # resend request are both sent back at the same time. The
            if msg.msg_type == fc.FixMsgType.RESEND_REQUEST:
                await self._handle_resend_request(msg)

            # if we are currently waiting on a resend request (of our own)
            # to complete then we ignore any messages that are our of
            # sequence  until resend is complete (this only applies for
            # the 'through infinity' strategy)
            if self._waiting_resend:
                return

            # if msg is a Logon<A>, process it before
            # sending a resend request
            if msg.msg_type == fc.FixMsgType.LOGON:
                await self._handle_logon(msg)

            # if msg is a Logout<5>, then there are several
            # scenarios to content with
            if msg.msg_type == fc.FixMsgType.LOGOUT:
                if self._waiting_logout_confirm:
                    await self.close()
                    return
                self._logout_after_resend = True

            # if msg is a SequenceReset<4>, then there are two scenarios
            # to contend with (GapFill and Reset)
            if msg.msg_type == fc.FixMsgType.SEQUENCE_RESET:
                # if Reset mode, simply set the next expected remote
                # seq number to the NewSeqNo(36) value of the msg
                if not self._is_gap_fill(msg):
                    new_seq_num = int(msg.get(self._tags.NewSeqNo))
                    await self._set_local_sequence(new_seq_num)
                    return

            await self._request_resend(
                start=error.expected,
                end=0
            )
        else:
            # ignore any SeqReset that attempts to lower the next expected
            # sequence number
            if msg.msg_type == fc.FixMsgType.SEQUENCE_RESET:
                new = int(msg.get(self._tags.NewSeqNo))
                expected = await self.get_remote_sequence()
                if new < expected:
                    return

            # TODO should we really be incrementing before processing?
            # what happens if we incr remote seq number then SeqReset
            # handler tries to set remote seq number to a lower number
            # as a result of this incr. Is this even possible? Need to
            # investigate.
            await self._incr_remote_sequence()

            if msg.is_duplicate:
                # if the msg is a duplicate and also an admin message,
                # then this is an erroneously re-sent admin messsage
                # and should be ignored

                # Note SequenceReset<4> is not included in the list of admin
                # messages, even though it is an admin message. This is because
                # SequenceReset<4> should still be processed event when
                # they have the PossDupFlag set to 'Y'.
                if msg.msg_type in ADMIN_MESSAGES:
                    return
            else:
                # if the msg is not a duplicate and we are waiting for
                # resend completion, then this signifies the end of resent
                # messages

                if self._waiting_resend:
                    self._waiting_resend = False
                    # if we received a Logout<5> that resulted in a
                    # sequence gap, then we must honor the Logout after
                    # resend is complete
                    if self._logout_after_resend:
                        await self._send_logoff()
                        return

            await self._dispatch(msg)

    async def _check_sequence_integrity(self, msg):
        actual = await self.get_remote_sequence()
        seq_num = msg.seq_num
        diff = seq_num - actual
        if diff == 0:
            return
        if diff >= 1:
            raise SequenceGap(seq_num, actual)
        raise FatalSequenceGap(seq_num, actual)

    async def _dispatch(self, msg):
        handler = {
            fc.FixMsgType.LOGON: self._handle_logon,
            fc.FixMsgType.TEST_REQUEST: self._handle_test_request,
            fc.FixMsgType.REJECT: self._handle_reject,
            fc.FixMsgType.RESEND_REQUEST: self._handle_resend_request,
            fc.FixMsgType.SEQUENCE_RESET: self._handle_sequence_reset,
        }.get(msg.msg_type)

        if handler is not None:
            await maybe_await(handler, msg)

    async def _handle_logon(self, msg):
        heartbeat_interval = int(msg.get(self._tags.HeartBtInt))
        if heartbeat_interval != self.config.get('heartbeat_interval'):
            await self._send_reject(
                msg=msg,
                tag=self._tags.HeartBtInt,
                rejection_type=fc.SessionRejectReason.VALUE_IS_INCORRECT,
                reason='HeartBtInt must be {}'.format(
                    self.config.get('heartbeat_interval'))
            )
            return

        target = msg.get(self._tags.TargetCompID)
        excepted_target = self.config.get('sender_comp_id')

        if target != excepted_target:
            await self._send_reject(
                msg=msg,
                tag=self._tags.TargetCompID,
                rejection_type=fc.SessionRejectReason.VALUE_IS_INCORRECT,
                reason='Target Comp ID is incorrect.'
            )
            return

        sender = msg.get(self._tags.SenderCompID)
        expected_sender = self.config.get('target_comp_id')

        if expected_sender is None:
            # if target_comp_id is not set in the config,
            # then we are implicitly allowing any target, so we
            # set target_comp_id to the target's send_comp_id.
            self.config['target_comp_id'] = expected_sender = sender

        if sender != expected_sender:
            await self._send_reject(
                msg=msg,
                tag=self._tags.TargetCompID,
                rejection_type=fc.SessionRejectReason.VALUE_IS_INCORRECT,
                reason='Sender Comp ID is incorrect.'
            )
            return

        is_reset = self._is_reset(msg)
        if is_reset:
            await self._set_remote_sequence(2)

        initiator = await self.get_initiator()
        if initiator != self.config['sender_comp_id']:
            await self._send_login(reset=is_reset)

    async def _handle_logout(self, msg):
        if self._waiting_logout_confirm:
            await self.close()
            return
        await self._send_logoff()

    async def _handle_test_request(self, msg):
        test_request_id = msg.get(self._tags.TestReqID)
        await self._send_heartbeat(test_request_id=test_request_id)

    async def _handle_reject(self, msg):
        reason = msg.get(self._tags.Text)
        print('Reject: {}'.format(reason))

    async def _handle_resend_request(self, msg):
        start = int(msg.get(self._tags.BeginSeqNo))
        end = int(msg.get(self._tags.EndSeqNo))
        if end == 0:
            # EndSeqNo of 0 means infinity
            end = float('inf')
        await self._resend_messages(start, end)

    async def _handle_sequence_reset(self, msg):
        if not self._is_gap_fill(msg):
            pass
        new_seq_num = int(msg.get(self._tags.NewSeqNo))
        await self._set_remote_sequence(new_seq_num)

    async def _cancel_heartbeat_timer(self):
        if self._hearbeat_cb is not None:
            self._hearbeat_cb.cancel()
            try:
                await self._hearbeat_cb
            except asyncio.CancelledError:
                pass
            self._hearbeat_cb = None

    async def _reset_heartbeat_timer(self):
        loop = asyncio.get_event_loop()
        await self._cancel_heartbeat_timer()
        self._hearbeat_cb = loop.create_task(
            self._set_heartbeat_timer())

    async def _set_heartbeat_timer(self):
        try:
            interval = self.config.get('heartbeat_interval')
            await asyncio.sleep(interval)
            await self._send_heartbeat()
        except asyncio.CancelledError:
            raise

    def _is_gap_fill(self, msg):
        gf_flag = msg.get(self._tags.GapFillFlag)
        return gf_flag == fc.GapFillFlag.YES

    def _is_reset(self, msg):
        reset_seq = msg.get(self._tags.ResetSeqNumFlag)
        return reset_seq == fc.ResetSeqNumFlag.YES

    @classmethod
    def register_scheme(cls, scheme, transport_cls):
        cls._registry.register_scheme(scheme, transport_cls)


class _FixSessionContextManager(Coroutine):

    def __init__(
        self,
        host,
        port,
        transport,
        on_connect=None,
        on_disconnect=None,
    ):
        self._host = host
        self._port = port
        self._transport = transport
        self._on_connect = on_connect
        self._on_disconnect = on_disconnect
        self._coro = self._connect()

    def __await__(self):
        return self._coro.__await__()

    async def __aenter__(self):
        await self._coro
        return self._transport

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._transport.close()
        if self._on_disconnect is not None:
            await maybe_await(self._on_disconnect)

    def send(self, arg):
        self._coro.send(arg)

    def throw(self, typ, val=None, tb=None):
        self._coro.throw(typ, val, tb)

    def close(self):
        self._coro.close()

    async def _connect(self):
        await self._transport.connect(self._host, self._port)
        if self._on_connect is not None:
            await maybe_await(self._on_connect)
