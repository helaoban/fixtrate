import asyncio
from collections import defaultdict
import datetime as dt
import logging
import uuid

import async_timeout

from . import helpers, constants as fc
from .exceptions import (
    SequenceGapError,
    FatalSequenceGapError,
    InvalidMessageError, FixRejectionError,
    IncorrectTagValueError, FIXError,
    InvalidTypeError, SessionError
)
from .factories import fix42
from .parse import FixParser
from .utils.aio import maybe_await

logger = logging.getLogger(__name__)

DEFAULT_OPTIONS = {
    'heartbeat_interval': 30,
    'receive_timeout': None,
    'fix_dict': None,
    'headers': []
}

DEAD = object()

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

    def __init__(
        self,
        session_id,
        store,
        transport,
        initiator=True,
        on_close=None,
        **kwargs
    ):
        self.store = store
        self.transport = transport
        self.config = get_options(**kwargs)
        self._session_id = session_id
        self._initiator = initiator
        self._on_close = on_close
        self._waiting_resend = False
        self._waiting_logout_confirm = False
        self._logout_after_resend = False
        self._hearbeat_cb = None
        self._callbacks = defaultdict(list)
        self._msg_queue = asyncio.Queue()
        self.logged_on = False
        self.parser = FixParser()
        self._ready = asyncio.Event()

        loop = asyncio.get_event_loop()
        loop.create_task(self._process_msg_queue())
        self._ready.set()

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            msg = await self.receive()
        except asyncio.TimeoutError as error:
            logger.error(error)
            raise StopAsyncIteration
        return msg

    @property
    def id(self):
        """ Returns the unique identifier for this session

        :return: str
        """
        return self._session_id

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
        return self.store.get_messages(self._session_id, *args, **kwargs)

    async def get_local_sequence(self):
        """ Return the current local sequence number.

        :rtype int
        """
        return await self.store.get_local(self._session_id)

    async def get_remote_sequence(self):
        """ Return the current remote sequence number.

        :rtype int
        """
        return await self.store.get_remote(self._session_id)

    async def logon(self):
        """ Logon to a FIX Session. Sends a Logon<A> message to peer.
        """
        if not self._initiator:
            raise FIXError(
                'Only a session initator can send '
                'a initate a logon')
        hb_int = self.config.get('heartbeat_interval')
        login_msg = fix42.logon(hb_int=hb_int)
        self.send(login_msg)

    async def reset(self):
        test_id = str(uuid.uuid4())
        test_request = fix42.test_request(test_id)
        self.send(test_request)
        await self.drain()
        self._ready.clear()
        self._msg_queue.put_nowait(None)
        self._register_msg_cb(
            fc.FixMsgType.HEARTBEAT, self._initiate_reset, test_id)

    async def logout(self):
        """ Logout from a FIX Session. Sends a Logout<5> message to peer.
        """
        rv = None
        self._waiting_logout_confirm = True
        self.send(fix42.logout())

    async def close(self):
        """
        Close the session. Closes the underlying connection and performs
        cleanup work.
        """
        self._msg_queue.put_nowait(DEAD)
        await self._cancel_heartbeat_timer()
        await self.transport.close()
        if self._on_close is not None:
            await maybe_await(self._on_close, self)

    def send(self, msg):
        """
        Send a FIX message to peer.

        :param msg: message to send.
        :type msg: :class:`~fixtrate.message.FixMessage`
        """
        self._msg_queue.put_nowait(msg)

    async def drain(self):
        await self._msg_queue.join()

    async def _send(self, msg):
        await self._append_standard_header(msg)
        if not msg.is_duplicate and not helpers.is_gap_fill(msg):
            await self._incr_local_sequence()

        await self._store_message(msg)

        try:
            await self.transport.write(msg.encode())
        except ConnectionError:
            await self.close()
            return

        await self._reset_heartbeat_timer()

    async def _append_standard_header(self, msg, timestamp=None):
        if msg.seq_num is None:
            seq_num = await self.get_local_sequence()
            msg.append_pair(fc.FixTag.MsgSeqNum, seq_num)

        headers = [
            (fc.FixTag.BeginString, self.id.begin_string),
            (fc.FixTag.SenderCompID, self.id.sender),
            (fc.FixTag.TargetCompID, self.id.target),
            *self.config['headers']
        ]

        for tag, val in headers:
            existing = msg.get(tag)
            if existing is None:
                msg.append_pair(tag, val, header=True)

        send_time = msg.get(fc.FixTag.SendingTime)
        if timestamp is not None or send_time is None:
            helpers.append_send_time(msg, timestamp=timestamp)

    async def _incr_local_sequence(self):
        return await self.store.incr_local(self._session_id)

    async def _incr_remote_sequence(self):
        return await self.store.incr_remote(self._session_id)

    async def _set_local_sequence(self, new_seq_num):
        return await self.store.set_local(self._session_id, new_seq_num)

    async def _set_remote_sequence(self, new_seq_num):
        return await self.store.set_remote(self._session_id, new_seq_num)

    async def _store_message(self, msg):
        try:
            await self.store.store_message(self._session_id, msg)
        except Exception as error:
            raise SessionError(
                'Unable to store message: %s' % error) from error

    async def _get_resend_msgs(self, start, end):
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
        sent_msgs = await self.store.get_sent(
            self.id, min=start, max=end)
        return helpers.prepare_msgs_for_resend(sent_msgs)

    async def _receive_msg(self, timeout=None):
        while True:
            msg = self.parser.get_message()
            if msg is not None:
                break
            try:
                with async_timeout.timeout(timeout):
                    data = await self.transport.read()
            except (asyncio.CancelledError, asyncio.TimeoutError):
                raise asyncio.TimeoutError
            except ConnectionError:
                # TODO does this session naturally close
                # at some point after (as a result of) this
                # exception?
                await self.close()
                raise
            self.parser.append_buffer(data)
        return msg

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
        msg = await self._receive_msg(timeout=timeout)
        if self.closed:
            raise ConnectionAbortedError
        await self._process_message(msg)
        return msg

    async def _process_message(self, msg):
        try:
            await self._validate_msg(msg)
        except InvalidMessageError as error:
            await self._handle_invalid_message(error)
            logger.warning(
                'Invalid message was received and rejected: '
                '%s' % msg.get(fc.FixTag.Text)
            )
        except FatalSequenceGapError as error:
            await self._handle_fatal_sequence_gap(
                error.fix_msg, error.gap)
        except SequenceGapError as error:
            await self._handle_sequence_gap(
                msg, error.gap)
        else:
            await self._handle_message(msg)
        for cb, *args in self._callbacks.pop(msg.msg_type, []):
            await maybe_await(cb, *args, msg)

    async def _validate_seq_num(self, msg):
        diff = await self._get_sequence_gap(msg)
        if diff > 0:
            raise SequenceGapError(msg, diff)
        if diff < 0:
            raise FatalSequenceGapError(msg, diff)

    async def _handle_invalid_message(self, error):
        reject_msg = helpers.make_reject_msg(
            error.fix_msg, error.tag, error.reject_type, str(error))
        self.send(reject_msg)

    async def _validate_msg(self, msg):
        helpers.validate_header(msg, self.id)
        if msg.msg_type == fc.FixMsgType.LOGON:
            hb_int = self.config['heartbeat_interval']
            helpers.validate_tag_value(
                msg, fc.FixTag.HeartBtInt, hb_int, int)
        await self._validate_seq_num(msg)

    async def _handle_message(self, msg):
        await self._store_message(msg)
        await self._incr_remote_sequence()

        if self._waiting_resend:
            if not msg.is_duplicate:
                self._waiting_resend = False
                if self._logout_after_resend:
                    return helpers.make_logout_msg()

        if not helpers.is_duplicate_admin(msg):
            handler = self._dispatch(msg)
            if handler is not None:
                await maybe_await(handler, msg)

    def _dispatch(self, msg):
        return {
            fc.FixMsgType.LOGON: self._handle_logon,
            fc.FixMsgType.LOGOUT: self._handle_logout,
            fc.FixMsgType.TEST_REQUEST: self._handle_test_request,
            fc.FixMsgType.REJECT: self._handle_reject,
            fc.FixMsgType.RESEND_REQUEST: self._handle_resend_request,
            fc.FixMsgType.SEQUENCE_RESET: self._handle_sequence_reset,
        }.get(msg.msg_type)

    async def _handle_sequence_gap(self, msg, gap):
        """ Handle sequence gap where gap > 0"

        Always honor a ResendRequest<2> from the peer no matter
        what, even if we are currently waiting for the peer
        to resend messages in response to our own ResendRequest<2>.
        This handles an edge case that occurs when both sides
        detect a sequence gap as a result of the respective
        Logon<A> messages. If after detecting a gap the peer
        sends both a Logon<A> message (the logon acknowledgment)
        AND a ResendRequest<2> AT THE SAME TIME, the following
        scenario occurs:
          1. We process the Logon<4> msg, detect a gap, and
             immediately issue our own ResendRequest<2> (using
             the 'through infinity' approach). This puts us into
             a 'waiting-on-resend' mode, which causes us to ignore
             any further out-of-sequence messages (where gap is > 0)
             until the resend is complete.
          2. We process the ResendRequest<2> which is also out-of-
             sequence (gap > 0). If we follow the 'waiting-on-resend'
             rule, then we should ignore this out-of-sequence msg and
             proceeed, but if we do that, the peer's ResendRequest<2>
             is not honored, and the FIX spec dictates that we must
             honor it, so we make an exception and proceed with
             message resend.

        If we are currently waiting on the peer to finish resending
        messages in response to a ResendRequest<2> of our own,
        then we ignore any messages that are out of sequence
        until the resend is complete. This only applies for
        the 'through infinity' strategy.

        If msg is a Logon<A>, process it before
        sending a ResendRequest<2> message.

        If we are waiting for a logout confirmation,
        then this is the ack for that logout, and we can
        can handle the logout message normally, this will
        close the session.

        If we were not waiting for a logout confirmation,
        then the peer is initiating a logout, and we will
        have to honour it after the peer finishes resending
        messages.

        If the message is a SequenceReset<4>, then there are two
        scenarios to contend with (GapFill and Reset).

        If GapFillFlag <123> is set to 'N' or does not exist,
        then this Sequence Reset <4> msg is in 'Reset' mode.
        In Reset mode, we simply set the next expected remote
        seq number to the NewSeqNo(36) value of the msg
        """
        if msg.msg_type == fc.FixMsgType.RESEND_REQUEST:
            await self._handle_resend_request(msg)

        if self._waiting_resend:
            return

        if msg.msg_type == fc.FixMsgType.SEQUENCE_RESET:
            # TODO how should we handle a GAP FILL here?
            if not helpers.is_gap_fill(msg):
                await self._handle_sequence_reset(msg)
                return

        if msg.msg_type == fc.FixMsgType.LOGON:
            await self._handle_logon(msg)

        if msg.msg_type == fc.FixMsgType.LOGOUT:
            if self._waiting_logout_confirm:
                await self._handle_logout(msg)
            else:
                self._logout_after_resend = True

        self._waiting_resend = True
        resend_request = helpers.make_resend_request(
            msg.seq_num - gap, 0)
        self.send(resend_request)

    async def _handle_fatal_sequence_gap(self, msg, gap):
        """ Handle a sequence gap where gap <0

        The sequence number of a SeqReset<4> message
        in 'Reset Mode' (GapFillFlag(123) not present
        or set to 'N') should be ignored,and by extension
        any resulting sequence gaps should also be ignored.

        A Logon<A> message with ResetSeqNumFlag(141)
        set to 'Y' will almost always result in a
        sequence gap where gap < 0, since it should
        be resetting the sequence number to 1. The
        reset request must be obeyed, and so the
        sequence gap is ignored.

        Ignore duplicate messages.

        If the message does not meet the above criteria,
        then we are in an unrecoverable situation, so we
        terminate the session and raise the error.

        """
        if helpers.is_reset_mode(msg):
            await self._handle_sequence_reset(msg)
        elif helpers.is_logon_reset(msg):
            await self._handle_logon_reset(msg)
        else:
            if not msg.is_duplicate:
                expected = msg.seq_num - gap
                logger.error(
                    'Unrecoverable sequence gap error. Received msg '
                    '(%s) with seq num %s, but expected seq num %s. '
                    'Terminating the session...' % (
                        msg.msg_type, msg.seq_num, expected)
                )
                await self.close()

    async def _get_sequence_gap(self, msg):
        expected = await self.get_remote_sequence()
        return msg.seq_num - expected

    async def _handle_logon(self, msg):
        if not self._initiator:
            hb_int = self.config['heartbeat_interval']
            reply = helpers.make_logon_msg(hb_int)
            self.send(reply)

        self.logged_on = True

    async def _handle_logon_reset(self, msg):
        hb_int = self.config['heartbeat_interval']
        reply = helpers.make_logon_msg(hb_int, reset=True)
        await self.store.reset(self._session_id)
        await self._set_remote_sequence(2)
        self.send(reply)

    async def _handle_logout(self, msg):
        if self._waiting_logout_confirm:
            self._waiting_logout_confirm = False
            await self.close()
        else:
            self._waiting_logout_confirm = True
            reply = helpers.make_logout_msg()
            self.send(reply)

        self.logged_on = False

    async def _handle_test_request(self, msg):
        test_request_id = msg.get(fc.FixTag.TestReqID)
        reply = fix42.heartbeat(test_request_id)
        self.send(reply)

    def _log_rejection(self, msg):
        reason = msg.get(fc.FixTag.Text)
        msg = 'Peer rejected message: %s' % reason
        logger.error(msg)

    def _handle_reject(self, msg):
        reason = msg.get(fc.FixTag.Text)
        self._log_rejection(msg)

    async def _handle_resend_request(self, msg):
        start = int(msg.get(fc.FixTag.BeginSeqNo))
        end = int(msg.get(fc.FixTag.EndSeqNo))
        if end == 0:
            # EndSeqNo of 0 means infinity
            end = float('inf')
        to_resend = await self._get_resend_msgs(start, end)
        for m in to_resend:
            self.send(m)

    async def _handle_sequence_reset(self, msg):
        new = int(msg.get(fc.FixTag.NewSeqNo))
        expected = await self.get_remote_sequence()

        if new < expected:
            error = (
                'SeqReset<4> attempting to decrease next '
                'expected sequence number. Current expected '
                'sequence number is %s, but SeqReset<4> is '
                'attempting to set the next expected sequence '
                'number to %s, this is now allowed.' % (expected, new)
            )
            reject_type = fc.SessionRejectReason.VALUE_IS_INCORRECT
            reject_msg = helpers.make_reject_msg(
                msg, fc.FixTag.NewSeqNo, reject_type, error)
            self.send(reject_msg)

        await self._set_remote_sequence(new)

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
            msg = fix42.heartbeat()
            self.send(msg)
        except asyncio.CancelledError:
            raise

    async def _initiate_reset(self, test_id, msg):
        if msg.get(fc.FixTag.TestReqID) == test_id:
            self._register_msg_cb(
                fc.FixMsgType.LOGON, self._confirm_reset)
            hb_int = self.config['heartbeat_interval']
            login_msg = fix42.logon(hb_int=hb_int, reset=True)
            await self.store.reset(self._session_id)
            await self._send(login_msg)
        else:
            cb = self._initiate_reset
            self._register_msg_cb(msg.msg_type, cb, test_id)

    async def _confirm_reset(self,  msg):
        if helpers.is_logon_reset(msg):
            await self._set_local_sequence(2)
            self._ready.set()
        else:
            self._register_msg_cb(
                msg.msg_type, self._confirm_reset)

    def _register_msg_cb(self, msg_type, func, *args):
        self._callbacks[msg_type].append((func, *args))

    async def _process_msg_queue(self):
        while True:
            await self._ready.wait()
            msg = await self._msg_queue.get()
            self._msg_queue.task_done()
            if msg is None:
                continue
            if msg is DEAD:
                break
            await self._send(msg)

