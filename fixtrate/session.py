import asyncio
import datetime as dt
import logging

import async_timeout

from . import constants as fc
from .exceptions import (
    SequenceGapError, FatalSequenceGapError,
    InvalidMessageError, FixRejectionError,
    IncorrectTagValueError, FIXError,
    InvalidTypeError
)
from .factories import fix42
from .parse import FixParser
from .utils.aio import maybe_await

logger = logging.getLogger(__name__)


ADMIN_MESSAGES = {
    fc.FixMsgType.LOGON,
    fc.FixMsgType.LOGOUT,
    fc.FixMsgType.HEARTBEAT,
    fc.FixMsgType.TEST_REQUEST,
    fc.FixMsgType.RESEND_REQUEST,
    fc.FixMsgType.SEQUENCE_RESET,
}

DEFAULT_OPTIONS = {
    'heartbeat_interval': 30,
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


class SessionID:
    def __init__(
        self,
        begin_string,
        sender_comp_id,
        target_comp_id,
        qualifier=None
    ):
        self.begin_string = begin_string
        self.sender_comp_id = sender_comp_id
        self.target_comp_id = target_comp_id
        self.qualifier = qualifier

    def __str__(self):
        return ':'.join(filter(None, (
            self.begin_string, self.sender_comp_id,
            self.target_comp_id, self.qualifier)))

    def __hash__(self):
        return hash(self.__str__())

    @property
    def target(self):
        return self.target_comp_id

    @property
    def sender(self):
        return self.sender_comp_id

    @property
    def fix_version(self):
        return self.begin_string

    @classmethod
    def from_dict(cls, dic):
        parts = {
            'begin_string',
            'sender_comp_id',
            'target_comp_id',
            'session_qualifier'
        }
        kw = {p: dic[p] for p in parts}
        return cls(**kw)

    @classmethod
    def from_str(cls, val, delimiter=':'):
        items = val.split(delimiter)[:4]
        return cls(*items)


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
        self.tags = self._get_tags(
            session_id.begin_string)

        self._session_id = session_id
        self._initiator = initiator
        self._on_close = on_close
        self._waiting_resend = False
        self._waiting_logout_confirm = False
        self._logout_after_resend = False
        self._hearbeat_cb = None

        self.logged_on = False
        self.parser = FixParser()

    def _get_tags(self, begin_string):
        tags = {
            fc.FixVersion.FIX42: fc.FixTag.FIX42,
            fc.FixVersion.FIX44: fc.FixTag.FIX44,
        }.get(begin_string)
        if tags is None:
            raise ValueError(
                '%s is an invalid or unsupported '
                'FIX version' % begin_string)
        return tags

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

    async def logon(self, reset=False):
        """ Logon to a FIX Session. Sends a Logon<A> message to peer.

        :param reset: Whether to set ResetSeqNumFlag to 'Y' on the
            Logon<A> message.
        :type reset: bool
        """
        if not self._initiator:
            raise FIXError(
                'Only a session initator can send '
                'a initate a logon')
        await self._send_login(reset)

    async def logout(self):
        """ Logout from a FIX Session. Sends a Logout<5> message to peer.
        """
        await self._send_logout()

    async def close(self):
        """
        Close the session. Closes the underlying connection and performs
        cleanup work.
        """
        await self._cancel_heartbeat_timer()
        await self.transport.close()
        if self._on_close is not None:
            await maybe_await(self._on_close, self)

    async def send(self, msg, skip_headers=False):
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

        try:
            await self.transport.write(msg.encode())
        except ConnectionError:
            await self.close()
            return

        await self._reset_heartbeat_timer()

    async def _incr_local_sequence(self):
        return await self.store.incr_local(self._session_id)

    async def _incr_remote_sequence(self):
        return await self.store.incr_remote(self._session_id)

    async def _set_local_sequence(self, new_seq_num):
        return await self.store.set_local(self._session_id, new_seq_num)

    async def _set_remote_sequence(self, new_seq_num):
        return await self.store.set_remote(self._session_id, new_seq_num)

    async def _store_message(self, msg):
        await self.store.store_message(self._session_id, msg)

    def _append_standard_header(
        self,
        msg,
        seq_num,
        timestamp=None
    ):
        pairs = (
            (self.tags.BeginString, self._session_id.begin_string),
            (self.tags.SenderCompID, self._session_id.sender),
            (self.tags.TargetCompID, self._session_id.target),
            (self.tags.MsgSeqNum, seq_num),
        )

        for tag, val in pairs:
            msg.append_pair(tag, val, header=True)

        timestamp = timestamp or dt.datetime.utcnow()
        msg.append_utc_timestamp(
            self.tags.SendingTime,
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

    async def _send_logout(self):
        if not self._waiting_logout_confirm:
            self._waiting_logout_confirm = True
            logout_msg = fix42.logout()
            await self.send(logout_msg)

    async def _request_resend(self, start, end):
        self._waiting_resend = True
        msg = fix42.resend_request(start, end)
        await self.send(msg)

    async def _send_gap_fill(self, seq_num, new_seq_num):
        msg = fix42.sequence_reset(new_seq_num)
        self._append_standard_header(msg, seq_num)
        await self.send(msg, skip_headers=True)

    async def _send_reset(self, new_seq_num):
        msg = fix42.sequence_reset(new_seq_num, gap_fill=False)
        # TODO what happens in there is a failure
        # here?
        await self.send(msg)

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
                    await self._send_gap_fill(gap_start, gap_end)
                    gap_start, gap_end = None, None
                msg.append_pair(
                    self.tags.PossDupFlag,
                    fc.PossDupFlag.YES,
                    header=True
                )
                await self.send(msg, skip_headers=True)

        if gap_start is not None:
            await self._send_gap_fill(gap_start, gap_end)

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
            await self._handle_message(msg)
        except InvalidMessageError as error:
            logger.error(
                'Invalid message was received and rejected: '
                '%s' % error
            )
            await self._send_reject(
                error.fix_msg, error.tag,
                error.reject_type, str(error))
        except FatalSequenceGapError as error:
            logger.error(
                'Unrecoverable sequence gap error. Received msg '
                '(%s) with seq num %s, but expected seq num %s. '
                'Terminating the session...' % (
                    msg.msg_type, msg.seq_num, error.expected)
            )
            await self.close()
            raise
        except SequenceGapError as error:
            logger.warning(str(error))
        except FixRejectionError as error:
            logger.error(str(error))

    async def _handle_message(self, msg):
        await self._validate_header(msg)
        await self._store_message(msg)

        try:
            await self._check_sequence_integrity(msg)
        except FatalSequenceGapError:
            if msg.msg_type == fc.FixMsgType.SEQUENCE_RESET:
                if not self._is_gap_fill(msg):
                    # The sequence number of a SeqReset<4> message
                    # in 'Reset Mode' (GapFillFlag(123) not present
                    # or set to 'N') should be ignored,and by extension
                    # any resulting sequence gaps should also be ignored.
                    await self._handle_sequence_reset(msg)
                    return

            if msg.msg_type == fc.FixMsgType.LOGON:
                if self._is_reset(msg):
                    # A Logon<A> message with ResetSeqNumFlag(141)
                    # set to 'Y' will almost always result in a
                    # sequence gap where gap < 0, since it should
                    # be resetting the sequence number to 1. The
                    # reset request must be obeyed, and so the
                    # sequence gap is ignored.
                    await self._handle_logon(msg)
                    return

            if msg.is_duplicate:
                # Ignore message if gap < 0 and PossDupFlaf = 'Y'
                # TODO this is a unique event during message resend,
                # need to make sure we handle properly
                return

            # All possible exceptions have been exhausted, and
            # this is now an unrecoverable situation, so we
            # terminate the session and raise the error.
            raise
        except SequenceGapError as error:
            if msg.msg_type == fc.FixMsgType.RESEND_REQUEST:
                # Always honor a ResendRequest<2> from the peer no matter
                # what, even if we are currently waiting for the peer
                # to resend messages in response to our own ResendRequest<2>.
                # This handles an edge case that occurs when both sides
                # detect a sequence gap as a result of the respective
                # Logon<A> messages. If after detecting a gap the peer
                # sends both a Logon<A> message (the logon acknowledgment)
                # AND a ResendRequest<2> AT THE SAME TIME, the following
                # scenario occurs:
                #   1. We process the Logon<4> msg, detect a gap, and
                #      immediately issue our own ResendRequest<2> (using
                #      the 'through infinity' approach). This puts us into
                #      a 'waiting-on-resend' mode, which causes us to ignore
                #      any further out-of-sequence messages (where gap is > 0)
                #      until the resend is complete.
                #   2. We process the ResendRequest<2> which is also out-of-
                #      sequence (gap > 0). If we follow the 'waiting-on-resend'
                #      rule, then we should ignore this out-of-sequence msg and
                #      proceeed, but if we do that, the peer's ResendRequest<2>
                #      is not honored, and the FIX spec dictates that we must
                #      honor it, so we make an exception and proceed with
                #      message resend.
                await self._handle_resend_request(msg)

            if self._waiting_resend:
                # If we are currently waiting on the peer to finish resending
                # messages in response to a ResendRequest<2> of our own,
                # then we ignore any messages that are out of sequence
                # until the resend is complete. This only applies for
                # the 'through infinity' strategy.
                return

            if msg.msg_type == fc.FixMsgType.LOGON:
                # If msg is a Logon<A>, process it before
                # sending a ResendRequest<2> message.
                await self._handle_logon(msg)

            if msg.msg_type == fc.FixMsgType.LOGOUT:
                if self._waiting_logout_confirm:
                    # If we are waiting for a logout confirmation,
                    # then this is the ack for that logout, and we can
                    # can handle the logout message normally, this will
                    # close the session.
                    await self._handle_logout(msg)
                    return
                else:
                    # If we were not waiting for a logout confirmation,
                    # then the peer is initiating a logout, and we will
                    # have to honour it after the peer finishes resending
                    # messages.
                    self._logout_after_resend = True

            # If the message is a SequenceReset<4>, then there are two
            # scenarios to contend with (GapFill and Reset).
            if msg.msg_type == fc.FixMsgType.SEQUENCE_RESET:
                # If GapFillFlag <123> is set to 'N' or does not exist,
                # then this Sequence Reset <4> msg is in 'Reset' mode.
                # In Reset mode, we simply set the next expected remote
                # seq number to the NewSeqNo(36) value of the msg

                # TODO how should we handle a GAP FILL here?
                if not self._is_gap_fill(msg):
                    await self._handle_sequence_reset(msg)
                    return

            await self._request_resend(
                start=error.expected,
                end=0
            )
        else:
            if msg.msg_type == fc.FixMsgType.SEQUENCE_RESET:
                # Reject any SeqReset<4> message that attempts
                # to lower the next expected sequence number
                tag = self.tags.NewSeqNo
                new = int(msg.get(tag))
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
                    raise InvalidMessageError(msg, tag, reject_type, error)

            await self._incr_remote_sequence()

            if msg.is_duplicate:
                if msg.msg_type in ADMIN_MESSAGES.difference({
                    fc.FixMsgType.SEQUENCE_RESET
                }):
                    # If the msg is a duplicate and also an admin message,
                    # then this is an erroneously re-sent admin messsage
                    # and should be ignored.
                    # An exception is made for SequenceReset<4> messages,
                    # which should always be processesed, even when
                    # PossDupFlag(43) is set to 'Y'. In fact, PossDupFlag(43)
                    # should always be set to 'Y' on SequenceReset<4> messages.
                    return
            else:
                if self._waiting_resend:
                    # If the msg is not a duplicate and we are waiting for
                    # resend completion, then this signifies the end of resent
                    # messages.
                    self._waiting_resend = False

                    if self._logout_after_resend:
                        # If we received a Logout<5> that resulted in a
                        # sequence gap, then we must honor the Logout<5>
                        # after resend is complete.
                        await self._send_logout()
                        return

            await self._dispatch(msg)

    def _validate_tag_value(self, msg, tag, expected, type_):
        actual = msg.get(tag)
        try:
            actual = type_(msg.get(tag))
        except (TypeError, ValueError) as error:
            raise InvalidTypeError(
                msg, tag, actual, type_) from error
        if actual != expected:
            raise IncorrectTagValueError(
                msg, tag, expected, actual)

    async def _validate_header(self, msg):
        for tag, value, type_ in (
            (self.tags.BeginString,  self._session_id.begin_string, str),
            (self.tags.TargetCompID,  self._session_id.sender, str),
            (self.tags.SenderCompID,  self._session_id.target, str)
        ):
            self._validate_tag_value(msg, tag, value, type_)

    async def _check_sequence_integrity(self, msg):
        actual = await self.get_remote_sequence()
        seq_num = msg.seq_num
        diff = seq_num - actual
        if diff == 0:
            return
        if diff >= 1:
            raise SequenceGapError(seq_num, actual)
        raise FatalSequenceGapError(seq_num, actual)

    async def _dispatch(self, msg):
        handler = {
            fc.FixMsgType.LOGON: self._handle_logon,
            fc.FixMsgType.LOGOUT: self._handle_logout,
            fc.FixMsgType.TEST_REQUEST: self._handle_test_request,
            fc.FixMsgType.REJECT: self._handle_reject,
            fc.FixMsgType.RESEND_REQUEST: self._handle_resend_request,
            fc.FixMsgType.SEQUENCE_RESET: self._handle_sequence_reset,
        }.get(msg.msg_type)

        if handler is not None:
            await maybe_await(handler, msg)

    async def _handle_logon(self, msg):
        is_reset = self._is_reset(msg)
        if is_reset:
            await self._set_remote_sequence(2)

        self._validate_tag_value(
            msg, self.tags.HeartBtInt,
            self.config['heartbeat_interval'], int)

        if not self._initiator:
            await self._send_login(reset=is_reset)

        self.logged_on = True

    async def _handle_logout(self, msg):
        if self._waiting_logout_confirm:
            self._waiting_logout_confirm = False
            await self.close()
        else:
            await self._send_logout()

        self.logged_on = False

    async def _handle_test_request(self, msg):
        test_request_id = msg.get(self.tags.TestReqID)
        await self._send_heartbeat(test_request_id=test_request_id)

    async def _handle_reject(self, msg):
        reason = msg.get(self.tags.Text)
        raise FixRejectionError(msg, reason)

    async def _handle_resend_request(self, msg):
        start = int(msg.get(self.tags.BeginSeqNo))
        end = int(msg.get(self.tags.EndSeqNo))
        if end == 0:
            # EndSeqNo of 0 means infinity
            end = float('inf')
        await self._resend_messages(start, end)

    async def _handle_sequence_reset(self, msg):
        new_seq_num = int(msg.get(self.tags.NewSeqNo))
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
        gf_flag = msg.get(self.tags.GapFillFlag)
        return gf_flag == fc.GapFillFlag.YES

    def _is_reset(self, msg):
        reset_seq = msg.get(self.tags.ResetSeqNumFlag)
        return reset_seq == fc.ResetSeqNumFlag.YES
