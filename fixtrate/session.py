import asyncio
from collections.abc import Coroutine
import datetime as dt
import logging
import socket

import async_timeout

from . import (
    constants as fc,
    exceptions as fe,
    parse,
    store as fix_store,
    utils,
)
from .config import Config
from .factories import fix42
from .signals import message_received, message_sent, sequence_gap

logger = logging.getLogger(__name__)


ADMIN_MESSAGES = [
    fc.FixMsgType.LOGON,
    fc.FixMsgType.LOGOUT,
    fc.FixMsgType.HEARTBEAT,
    fc.FixMsgType.TEST_REQUEST,
    fc.FixMsgType.RESEND_REQUEST,
]


class FixSessionId:

    def __init__(
        self,
        begin_string,
        sender_comp_id,
        target_comp_id,
        session_qualifier=None
    ):
        self.__dict__['begin_string'] = begin_string
        self.__dict__['sender_comp_id'] = sender_comp_id
        self.__dict__['target_comp_id'] = target_comp_id
        self.__dict__['session_qualifier'] = session_qualifier

    def __eq__(self, other):
        if isinstance(other, FixSessionId):
            return self.__str__() == other.__str__()
        return NotImplemented

    def __str__(self):

        parts = [
            self.begin_string,
            self.sender_comp_id,
            self.target_comp_id
        ]

        if self.session_qualifier is not None:
            parts.append(self.session_qualifier)

        return ':'.join(parts)

    def __setattr__(self, name, value):
        raise TypeError('FixSessionId objects are immutable')


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
        version,
        sender_comp_id,
        target_comp_id,
        heartbeat_interval=30,
        conf=None,
        store=None,
        dictionary=None,
        debug=False,
        receive_timeout=None,
        headers=None,
        loop=None,
    ):
        conf = conf or Config.from_env()
        self._config = conf

        try:
            self._version = fc.FixVersion(version)
        except ValueError:
            raise fe.InvalidFIXVersion(version)

        self._sender_comp_id = sender_comp_id
        self._target_comp_id = target_comp_id
        self._session_id = FixSessionId(
            self._version, self._sender_comp_id, self._target_comp_id)
        self._heartbeat_interval = heartbeat_interval

        self._headers = headers or []

        self._tags = getattr(fc.FixTag, self._version.name)
        self._store = store or fix_store.FixMemoryStore()
        self._parser = parse.FixParser()
        self._fix_dict = dictionary

        self._is_resetting = False
        self._conn = None
        self._hearbeat_cb = None
        self._loop = loop or asyncio.get_event_loop()
        self._debug = self._config.get('DEBUG', debug)
        self._receive_timeout = receive_timeout
        self._is_initiator = utils.Tristate(None)

        self._waiting_resend = False
        self._waiting_logout_confirm = False
        self._logout_after_resend = False

        self.on_recv_msg_funcs = []
        self.on_send_msg_funcs = []

        self._closing = False
        self._closed = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        msg = await self._recv_msg()
        if msg is None:
            raise StopAsyncIteration
        return msg

    @property
    def closed(self):
        """ Read-only property. Returns True fs underlying connection
        has been closed.

        :return: bool
        """
        return self._conn is None or self._conn.closed

    def connect(self, address):
        """
        Coroutine that waits for a successfuly connection to a FIX peer.
        Returns a FixConnection object. Can also be used as an async context
        manager, in which case the connection is automatically closed on
        exiting the context manager.

        :param address: tuple of (ip, port)
        :return: :class:`FixConnection` object
        :rtype: FixConnection
        """

        host, port = address

        try:
            'localhost' or socket.inet_aton(host)
        except OSError:
            raise ValueError('{} is not a legal IP address'.format(host))

        return _FixConnectionContextManager(
            host=host,
            port=port,
            on_connect=self._on_connect,
            on_disconnect=self._on_disconnect,
            loop=self._loop
        )

    async def listen(self, reader, writer):
        """ Listen on a given connection object. Useful for having a FIX session
        listen on an existing connection (for example when serving many clients
        from a server).

        :param reader: StreamReader object
        :type reader: :class:`~asyncio.StreamReader`
        :param writer: StreamWriter object
        :type writer: :class:`~asyncio.StreamWriter`
        """
        conn = FixConnection(
            reader=reader,
            writer=writer,
            on_disconnect=self._on_disconnect
        )
        await self._on_connect(conn)

    async def receive(self, timeout=None):
        """ Coroutine that waits for message from peer and returns it.

        :param timeout: (optional) timeout in seconds. If specified, method
            will raise asyncio.TimeoutError if message in not
            received after timeout. Defaults to `None`.
        :type timeout: float, int or None

        :return: :class:`~fixtrate.message.FixMessage` object
        """
        return await self._recv_msg(timeout)

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
        msg = fix42.logoff()
        await self.send_message(msg)

    async def close(self):
        """
        Close the session. Closes the underlying connection and performs
        cleanup work.
        """
        if not self.closed:
            await self._close()

    async def send_message(self, msg, skip_headers=False):
        """
        Send a FIX message to peer.

        :param msg: message to send.
        :type msg: :class:`~fixtrate.message.FixMessage`
        :param bool skip_headers: (optional) If set to `True`, the session will
            not append the standard header before sending. Defaults to `False`
        """
        if not skip_headers:
            seq_num = await self._store.get_seq_num()
            self._append_standard_header(msg, seq_num)

        if not msg.is_duplicate and not self._is_gap_fill(msg):
            await self._store.incr_seq_num()

        await self._store.store_message(msg)

        for func in self.on_send_msg_funcs:
            await utils.maybe_await(func, msg)

        message_sent.send(self, msg=msg)

        await self._conn.write(msg.encode())
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

    async def _close(self):
        self._closing = True
        logger.info('Shutting down...')
        await self._cancel_heartbeat_timer()
        if self._conn is not None and not self._conn.closed:
            await self._conn.close()

        self._closed = True

    async def _on_connect(self, conn):
        self._conn = conn
        await self._store.store_config(self._config)

    async def _on_disconnect(self):
        if not self._closing:
            await self._close()

    def _append_standard_header(
        self,
        msg,
        seq_num,
        timestamp=None
    ):
        pairs = (
            (self._tags.BeginString, self._version),
            (self._tags.SenderCompID, self._sender_comp_id),
            (self._tags.TargetCompID, self._target_comp_id),
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

        for tag, val in self._headers:
            msg.append_pair(tag, val, header=True)

    async def _send_heartbeat(self, test_request_id=None):
        msg = fix42.heartbeat(test_request_id)
        await self.send_message(msg)

    async def _send_test_request(self, test_request_id):
        msg = fix42.test_request(test_request_id)
        await self.send_message(msg)

    async def _send_reject(self, msg, tag, rejection_type, reason):
        msg = fix42.reject(
            ref_sequence_number=msg.seq_num,
            ref_message_type=msg.msg_type,
            ref_tag=tag,
            rejection_type=rejection_type,
            reject_reason=reason,
        )
        await self.send_message(msg)

    async def _send_login(self, reset=False):

        if self._is_initiator == None:
            self._is_initiator = utils.Tristate(True)

        if self._is_initiator == False:
            self._is_initiator = utils.Tristate(None)

        login_msg = fix42.logon(
            heartbeat_interval=self._heartbeat_interval,
            reset_sequence=reset
        )
        if reset:
            await self._store.set_seq_num(1)
            self._append_standard_header(login_msg, seq_num=1)
            await self.send_message(login_msg, skip_headers=True)
        else:
            await self.send_message(login_msg)

    async def _send_logout(self):
        if self._waiting_logout_confirm:
            # TODO what happends if Logout<5> sent twice?
            return
        logout_msg = fix42.logoff()
        await self.send_message(logout_msg)

    async def _request_resend(self, start, end):
        self._waiting_resend = True
        msg = fix42.resend_request(start, end)
        await self.send_message(msg)

    async def _send_sequence_reset(self, seq_num, new_seq_num):
        msg = fix42.sequence_reset(new_seq_num)
        self._append_standard_header(msg, seq_num)
        await self.send_message(msg, skip_headers=True)

    async def _resend_messages(self, start, end):
        # TODO support for end=0 must either be enforced here or in
        # the store!

        # TODO support for skipping the resend of certain business messages
        # based on config options (eg. stale order requests)

        gf_seq_num,  gf_new_seq_num = None, None
        async for msg in await self._store.get_messages(
                min=start, max=end, direction='sent'):
            seq_num = msg.get(32)
            if msg.msg_type in ADMIN_MESSAGES:
                if gf_seq_num is None:
                    gf_seq_num = seq_num
                gf_new_seq_num = seq_num + 1
            else:
                if gf_new_seq_num is not None:
                    await self._send_sequence_reset(gf_seq_num, gf_new_seq_num)
                    gf_seq_num, gf_new_seq_num = None, None
                msg.append_pair(
                    self._tags.PossDupFlag,
                    fc.PossDupFlag.YES,
                    header=True
                )
                await self.send_message(msg, skip_headers=True)

        if gf_seq_num is not None:
            await self._send_sequence_reset(gf_seq_num, gf_new_seq_num)

    async def _recv_msg(self, timeout=None):
        while True:
            msg = self._parser.get_message()
            if msg:
                break
            try:
                with async_timeout.timeout(
                    timeout or self._receive_timeout,
                    loop=self._loop
                ):
                    data = await self._conn.read()
            except (asyncio.CancelledError, asyncio.TimeoutError):
                raise asyncio.TimeoutError
            except ConnectionError:
                break
            self._parser.append_buffer(data)

        if self._closing or self._closed:
            return None

        if msg:
            await self._handle_message(msg)
        return msg

    async def _handle_message(self, msg):
        await self._store.store_message(msg)

        for func in self.on_recv_msg_funcs:
            await utils.maybe_await(func, msg)

        message_received.send(self, msg=msg)

        try:
            await self._check_sequence_integrity(msg)
        except fe.FatalSequenceGap:
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
        except fe.SequenceGap as error:
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
                    await self._close()
                    return
                self._logout_after_resend = True

            # if msg is a SequenceReset<4>, then there are two scenarios
            # to contend with (GapFill and Reset)
            if msg.msg_type == fc.FixMsgType.SEQUENCE_RESET:
                # if Reset mode, simply set the next expected remote
                # seq number to the NewSeqNo(36) value of the msg
                if not self._is_gap_fill(msg):
                    new_seq_num = int(msg.get(self._tags.NewSeqNo))
                    await self._store.set_seq_num(new_seq_num)
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
                expected = await self._store.get_seq_num(remote=True)
                if new < expected:
                    return

            # TODO should we really be incrementing before processing?
            # what happens if we incr remote seq number then SeqReset
            # handler tries to set remote seq number to a lower number
            # as a result of this incr. Is this even possible? Need to
            # investigate.
            await self._store.incr_seq_num(remote=True)

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
                        await self._send_logout()
                        return

            await self._dispatch(msg)

    async def _check_sequence_integrity(self, msg):
        actual = await self._store.get_seq_num(remote=True)
        diff = msg.seq_num - actual
        if diff == 0:
            return
        if diff >= 1:
            raise fe.SequenceGap(msg.seq_num, actual)
        raise fe.FatalSequenceGap(msg.seq_num, actual)

    async def _dispatch(self, msg):
        handler = {
            fc.FixMsgType.LOGON: self._handle_logon,
            fc.FixMsgType.TEST_REQUEST: self._handle_test_request,
            fc.FixMsgType.REJECT: self._handle_reject,
            fc.FixMsgType.RESEND_REQUEST: self._handle_resend_request,
            fc.FixMsgType.SEQUENCE_RESET: self._handle_sequence_reset,
        }.get(msg.msg_type)

        if handler is not None:
            await utils.maybe_await(handler, msg)

    async def _handle_logon(self, msg):
        heartbeat_interval = int(msg.get(self._tags.HeartBtInt))
        if heartbeat_interval != self._heartbeat_interval:
            await self._send_reject(
                msg=msg,
                tag=self._tags.HeartBtInt,
                rejection_type=fc.SessionRejectReason.VALUE_IS_INCORRECT,
                reason='HeartBtInt must be {}'.format(
                    self._heartbeat_interval)
            )
            return

        target_comp_id = msg.get(self._tags.TargetCompID)
        if target_comp_id != self._sender_comp_id:
            await self._send_reject(
                msg=msg,
                tag=self._tags.TargetCompID,
                rejection_type=fc.SessionRejectReason.VALUE_IS_INCORRECT,
                reason='Target Comp ID is incorrect.'
            )
            return

        is_reset = self._is_reset(msg)
        if is_reset:
            await self._store.set_seq_num(2, remote=True)

        if self._is_initiator == None:
            self._is_initiator = utils.Tristate(False)
            await self._send_login(reset=is_reset)

        if self._is_initiator == True:
            self._is_initiator = utils.Tristate(None)

    async def _handle_logout(self, msg):
        if self._waiting_logout_confirm:
            await self._close()
            return
        await self._send_logout()

    async def _handle_test_request(self, msg):
        test_request_id = msg.get(self._tags.TestReqID)
        await self._send_heartbeat(test_request_id=test_request_id)

    async def _handle_reject(self, msg):
        reason = msg.get(self._tags.Text)
        print('Reject: {}'.format(reason))

    async def _handle_resend_request(self, msg):
        start = msg.get(self._tags.BeginSeqNo)
        end = msg.get(self._tags.EndSeqNo)
        await self._resend_messages(int(start), int(end))

    async def _handle_sequence_reset(self, msg):
        if not self._is_gap_fill(msg):
            pass
        new_seq_num = int(msg.get(self._tags.NewSeqNo))
        await self._store.set_seq_num(new_seq_num, remote=True)

    async def _cancel_heartbeat_timer(self):
        if self._hearbeat_cb is not None:
            self._hearbeat_cb.cancel()
            try:
                await self._hearbeat_cb
            except asyncio.CancelledError:
                pass
            self._hearbeat_cb = None

    async def _reset_heartbeat_timer(self):
        await self._cancel_heartbeat_timer()
        self._hearbeat_cb = self._loop.create_task(
            self._set_heartbeat_timer())

    async def _set_heartbeat_timer(self):
        try:
            interval = self._heartbeat_interval
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


class FixConnection:

    def __init__(
        self,
        reader,
        writer,
        on_disconnect=None,
        loop=None
    ):
        self._reader = reader
        self._writer = writer
        self._on_disconnect = on_disconnect
        self._loop = loop or asyncio.get_event_loop()
        self.connected = True

    @property
    def closed(self):
        return not self.connected

    async def close(self):

        if not self.connected:
            return

        self._writer.close()
        self.connected = False

        if self._on_disconnect is not None:
            await utils.maybe_await(self._on_disconnect)

    async def read(self):
        try:
            data = await self._reader.read(4096)
        except ConnectionError as error:
            logger.error(error)
            await self.close()
            raise
        if data == b'':
            logger.error('Peer closed the connection!')
            await self.close()
            raise ConnectionAbortedError
        return data

    async def write(self, *args, **kwargs):
        self._writer.write(*args, **kwargs)
        try:
            await self._writer.drain()
        except ConnectionError as error:
            logger.error(error)
            await self.close()


class _FixConnectionContextManager(Coroutine):

    def __init__(
        self,
        host='localhost',
        port=4000,
        on_connect=None,
        on_disconnect=None,
        loop=None
    ):
        self._host = host
        self._port = port
        self._on_connect = on_connect
        self._on_disconnect = on_disconnect
        self._loop = loop or asyncio.get_event_loop()
        self._coro = self._connect()

    def __await__(self):
        return self._coro.__await__()

    async def __aenter__(self):
        self._conn = await self._coro
        return self._conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._conn.close()

    def send(self, arg):
        self._coro.send(arg)

    def throw(self, typ, val=None, tb=None):
        self._coro.throw(typ, val, tb)

    def close(self):
        self._coro.close()

    async def _connect(self, tries=5, retry_wait=5):
        tried = 1
        while tried <= tries:
            try:
                reader, writer = await asyncio.open_connection(
                    host=self._host,
                    port=self._port,
                    loop=self._loop
                )
            except OSError as error:
                logger.error(error)
                logger.info('Connection failed, retrying in {} seconds...'
                            ''.format(retry_wait))
                tried += 1
                await asyncio.sleep(retry_wait)
                continue
            else:
                conn = FixConnection(
                    reader, writer, on_disconnect=self._on_disconnect)
                await utils.maybe_await(self._on_connect, conn)
                return conn

        logger.info('Connection tries ({}) exhausted'.format(tries))
        raise ConnectionError
