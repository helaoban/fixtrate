import asyncio
from collections.abc import Coroutine
import datetime as dt
import logging

from fixation import (
    constants as fc,
    utils, exceptions as fe, parse,
    store as fix_store, config
)
from fixation.factories import fix42


logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

ADMIN_MESSAGES = [
    fc.FixMsgType.Logon,
    fc.FixMsgType.Logout,
    fc.FixMsgType.Heartbeat,
    fc.FixMsgType.TestRequest,
    fc.FixMsgType.ResendRequest,
    fc.FixMsgType.SequenceReset,
    fc.FixMsgType.Reject,
]


class FixConnection(object):

    def __init__(
        self,
        reader,
        writer,
        on_disconnect=None,
        loop=None
    ):
        self.reader = reader
        self.writer = writer
        self.on_disconnect = on_disconnect
        self.loop = loop or asyncio.get_event_loop()
        self.connected = True

    async def close(self):
        self.writer.close()
        self.connected = False

        if self.on_disconnect is not None:
            utils.maybe_await(self.on_disconnect)

    async def read(self):
        return await self.reader.read(4096)

    async def write(self, *args, **kwargs):
        self.writer.write(*args, **kwargs)
        await self.writer.drain()


class FixConnectionContextManager(Coroutine):

    def __init__(
        self,
        conf,
        on_connect=None,
        on_disconnect=None,
        is_server=False,
        loop=None
    ):
        self.config = conf
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.loop = loop or asyncio.get_event_loop()
        self._coro = self._listen() if is_server else self._connect()
        self._server = None

    async def _connect(self, tries=5, retry_wait=5):
        host = self.config.get('FIX_HOST', '127.0.0.1')
        port = self.config.get('FIX_PORT', 4000)
        tried = 1
        while tried <= tries:
            try:
                reader, writer = await asyncio.open_connection(
                    host=host,
                    port=port,
                    loop=self.loop
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
                    reader, writer, self.on_disconnect)
                utils.maybe_await(self.on_connect, conn)
                return conn

        logger.info('Connection tries ({}) exhausted'.format(tries))
        raise ConnectionError

    async def _listen(self):
        queue = asyncio.Queue()

        async def put(reader, writer):
            _conn = FixConnection(
                reader, writer, self.on_disconnect)
            await queue.put(_conn)

        host = self.config.get('FIX_HOST', '127.0.0.1')
        port = self.config.get('FIX_PORT', 4000)
        await asyncio.start_server(
            put,
            host=host,
            port=port,
            backlog=1
        )
        conn = await queue.get()
        utils.maybe_await(self.on_connect, conn)
        return conn

    def send(self, arg):
        self._coro.send(arg)

    def throw(self, typ, val=None, tb=None):
        self._coro.throw(typ, val, tb)

    def close(self):
        self._coro.close()

    def __await__(self):
        return self._coro.__await__()

    async def __aenter__(self):
        self._conn = await self._coro
        return self._conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._conn.close()


class FixSession:
    """
    FIX Session Manager
    """
    def __init__(
        self,
        conf=None,
        store=None,
        dictionary=None,
        loop=None,
        debug=False
    ):
        conf = conf or config.get_config_from_env()
        config.validate_config(conf)
        self._config = conf

        self._tags = getattr(fc.FixTag, self._config['FIX_VERSION'].name)
        self._store = store or fix_store.FixRedisStore()
        self._parser = parse.FixParser(self._config)
        self._fix_dict = dictionary

        self._is_resetting = False
        self._connection = None
        self._hearbeat_cb = None
        self._loop = loop or asyncio.get_event_loop()
        self._debug = self._config.get('FIX_DEBUG', debug)

        self._is_initiator = utils.Tristate(None)

    def _print_msg_to_console(self, msg, remote=False):
        send_time = msg.get(self._tags.SendingTime)
        direction = '<--' if remote else '-->'
        print('{}: {} {}'.format(send_time, msg.msg_type, direction))

    def connect(self):
        self._is_initiator = utils.Tristate(True)
        return FixConnectionContextManager(
            self._config, self._on_connect, self._on_disconnect)

    def listen(self):
        self._is_initiator = utils.Tristate(False)
        return FixConnectionContextManager(
            self._config, self._on_connect, self._on_disconnect, is_server=True)

    async def _on_connect(self, conn):
        self._connection = conn
        self._store.store_config(self._config)

    async def _on_disconnect(self):
        await self._close()

    def _append_standard_header(
        self,
        msg,
        seq_num,
        timestamp=None
    ):
        """
        Create a base message with standard headers set.
        BodyLength and Checksum are handled by SimpleFix

        :param msg:
        :param timestamp:
        :return:
        """
        msg.append_pair(
            self._tags.BeginString,
            self._config['FIX_VERSION'],
            header=True
        )
        msg.append_pair(
            self._tags.SenderCompID,
            self._config['FIX_SENDER_COMP_ID'],
            header=True
        )
        msg.append_pair(
            self._tags.TargetCompID,
            self._config['FIX_TARGET_COMP_ID'],
            header=True
        )
        msg.append_pair(
            self._tags.MsgSeqNum,
            seq_num,
            header=True
        )

        if timestamp is None:
            timestamp = dt.datetime.utcnow()

        msg.append_utc_timestamp(
            self._tags.SendingTime,
            timestamp=timestamp,
            precision=6,
            header=True
        )

    async def send_message(self, msg, skip_headers=False):
        if not skip_headers:
            seq_num = self._store.get_seq_num()
            self._append_standard_header(msg, seq_num)
        if self._debug:
            self._print_msg_to_console(msg)
        await self._connection.write(msg.encode())
        self._store.incr_seq_num()
        self._store.store_message(msg)
        await self._reset_heartbeat_timer()

    async def _send_heartbeat(self, test_request_id=None):
        msg = fix42.heartbeat(test_request_id)
        await self.send_message(msg)

    async def _send_test_request(self, test_request_id):
        msg = fix42.test_request(test_request_id)
        await self.send_message(msg)

    async def _send_sequence_reset(self):
        seq_num = self._store.get_seq_num()
        msg = fix42.sequence_reset(seq_num + 1)
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

    async def _send_login(self):
        login_msg = fix42.logon(
            heartbeat_interval=self._config['FIX_HEARTBEAT_INTERVAL'],
            reset_sequence=self._is_resetting
        )
        await self.send_message(login_msg)

    async def logon(self, reset=False):
        """
        Send a Logon <A> message. Note: setting reset_sequence=True will
        set the ResetSeqNumFlag to 'Y', which for most counter-parties
        means opening new FIX session, and so we clear the store.

        :return:
        """
        self._is_resetting = reset
        if self._is_resetting:
            self._store.new_session()

        await self._send_login()

    async def logoff(self):
        msg = fix42.logoff()
        await self.send_message(msg)

    async def _request_resend(self, start, end):
        msg = fix42.resend_request(start, end)
        await self.send_message(msg)

    async def _reset_sequence(self, new_seq_num):
        self._store.set_remote_sequence_number(new_seq_num - 1)
        msg = fix42.sequence_reset(new_seq_num)
        await self.send_message(msg)

    async def _resend_messages(self, start, end):
        sent_messages = self._store.get_messages_by_seq_num(
            start=start, end=end, remote=False)

        gf_seq_num,  gf_new_seq_num = None, None
        for seq_num, msg in sent_messages.items():
            if msg.msg_type in ADMIN_MESSAGES:
                if gf_seq_num is None:
                    gf_seq_num = seq_num
                gf_new_seq_num = seq_num + 1
            else:
                if gf_new_seq_num is not None:
                    await self._reset_sequence(
                        new_seq_num=gf_new_seq_num)
                    gf_seq_num, gf_new_seq_num = None, None

                msg.append_pair(
                    self._tags.PossDupFlag,
                    fc.PossDupFlag.YES,
                    header=True
                )
                await self.send_message(msg, skip_headers=True)

    def _check_sequence_integrity(self, msg):
        actual = self._store.get_seq_num(remote=True)
        diff = msg.seq_num - actual
        if diff == 0:
            return
        if diff >= 1:
            raise fe.SequenceGap(msg.seq_num, actual)
        raise fe.FatalSequenceGap(msg.seq_num, actual)

    async def _dispatch(self, msg):
        handler = {
            fc.FixMsgType.Logon: self._handle_logon,
            fc.FixMsgType.TestRequest: self._handle_test_request,
            fc.FixMsgType.Reject: self._handle_reject,
            fc.FixMsgType.ResendRequest: self._handle_resend_request,
            fc.FixMsgType.SequenceReset: self._handle_sequence_reset,
        }.get(msg.msg_type)

        if handler is not None:
            await utils.maybe_await(handler, msg)

    def _is_gap_fill(self, msg):
        gf_flag = msg.get(self._tags.GapFillFlag)
        return gf_flag == fc.GapFillFlag.YES

    async def _handle_message(self, msg):

        self._store.store_message(msg, remote=True)

        try:
            self._check_sequence_integrity(msg)
        except fe.FatalSequenceGap as error:
            logger.exception(error)

            if msg.is_duplicate:
                return

            if msg.msg_type == fc.FixMsgType.SequenceReset:
                if not self._is_gap_fill(msg):
                    await self._handle_sequence_reset(msg)
                    return

            await self.close()
            raise
        except fe.SequenceGap as error:

            if msg.msg_type == fc.FixMsgType.Logon:
                await self._handle_logon(msg)
                await self._request_resend(
                    start=error.expected + 1,
                    end=0
                )

            if msg.msg_type == fc.FixMsgType.Logout:
                # TODO handle logout sequence gap case
                pass

            if msg.msg_type == fc.FixMsgType.ResendRequest:
                await self._handle_resend_request(msg)
                await self._request_resend(
                    start=error.expected + 1,
                    end=0
                )

            if msg.msg_type == fc.FixMsgType.SequenceReset:
                if self._is_gap_fill(msg):
                    await self._request_resend(
                        start=error.expected + 1,
                        end=0
                    )
                else:
                    new_seq_num = int(msg.get(self._tags.NewSeqNo))
                    self._store.set_seq_num(new_seq_num)
            return
        finally:
            self._store.incr_seq_num(remote=True)

        await self._dispatch(msg)

    async def _handle_sequence_reset(self, msg):
        if not self._is_gap_fill(msg):
            pass
        new_seq_num = int(msg.get(self._tags.NewSeqNo))
        self._store.set_seq_num(new_seq_num - 1, remote=True)

    async def _handle_logon(self, msg):
        """
        Handle a Logon <A> message sent from server. The only
        action that needs to be taken is when we have set
        ResetSeqNumFlag <141> to 'Y' in our own Logon <A> message.
        In that case, we have initiated a new session,
        the server has reset it's own sequence
        numbers and we need reflect that change in the store.

        :param msg:
        :return:
        """
        heartbeat_interval = int(msg.get(self._tags.HeartBtInt))
        if heartbeat_interval != self._config['FIX_HEARTBEAT_INTERVAL']:
            await self._send_reject(
                msg=msg,
                tag=self._tags.HeartBtInt,
                rejection_type=fc.SessionRejectReason.VALUE_IS_INCORRECT,
                reason='HeartBtInt must be {}'.format(
                    self._config['FIX_HEARTBEAT_INTERVAL'])
            )
            return

        target_comp_id = msg.get(self._tags.TargetCompID)
        if target_comp_id != self._config['FIX_SENDER_COMP_ID']:
            await self._send_reject(
                msg=msg,
                tag=self._tags.TargetCompID,
                rejection_type=fc.SessionRejectReason.VALUE_IS_INCORRECT,
                reason='Target Comp ID is incorrect.'
            )
            return

        if self._is_resetting:
            self._store.set_seq_num(msg.seq_num, remote=True)
            self._is_resetting = False

        reset_seq = msg.get(self._tags.ResetSeqNumFlag)
        if reset_seq == fc.ResetSeqNumFlag.YES:
            self._store.set_seq_num(msg.seq_num, remote=True)

        logger.debug('Login successful!')

        if self._is_initiator == False:
            await self._send_login()

    async def _handle_resend_request(self, msg):
        start_sequence_number = int(msg.get(self._tags.BeginSeqNo))
        end_sequence_number = int(msg.get(self._tags.EndSeqNo))
        await self._resend_messages(start_sequence_number, end_sequence_number)

    async def _handle_test_request(self, msg):
        test_request_id = msg.get(self._tags.TestReqID)
        await self._send_heartbeat(test_request_id=test_request_id)

    async def _handle_reject(self, msg):
        reject_reason = msg.get(self._tags.Text)
        print('Reject: {}'.format(reject_reason))

    async def _recv_msg(self):
        while True:
            msg = self._parser.get_message()
            if msg:
                break

            try:
                data = await self._connection.read()
            except ConnectionError as error:
                logger.error(error)
                return
            if data == b'':
                logger.error('Peer closed the connection!')
                return
            self._parser.append_buffer(data)

        if self._debug:
            self._print_msg_to_console(msg, remote=True)

        await self._handle_message(msg)
        return msg

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
            interval = self._config['FIX_HEARTBEAT_INTERVAL']
            await asyncio.sleep(interval)
            await self._send_heartbeat()
        except asyncio.CancelledError:
            raise

    def __aiter__(self):
        return self

    async def __anext__(self):
        msg = await self._recv_msg()
        if msg is None:
            raise StopAsyncIteration
        return msg

    async def _close(self):
        await self._cancel_heartbeat_timer()
        logger.info('Shutting down...')

    async def close(self):
        await self._close()
        if self._connection.connected:
            await self._connection.close()
