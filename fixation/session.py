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
from .signals import message_received, message_sent, sequence_gap


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


class FixConnectionContextManager(Coroutine):

    def __init__(
        self,
        conf,
        on_connect=None,
        on_disconnect=None,
        loop=None
    ):
        self._config = conf
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
        host = self._config.get('FIX_HOST', '127.0.0.1')
        port = self._config.get('FIX_PORT', 4000)
        tried = 1
        while tried <= tries:
            try:
                reader, writer = await asyncio.open_connection(
                    host=host,
                    port=port,
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
        self._store = store or fix_store.FixMemoryStore()
        self._parser = parse.FixParser(self._config)
        self._fix_dict = dictionary

        self._is_resetting = False
        self._conn = None
        self._hearbeat_cb = None
        self._loop = loop or asyncio.get_event_loop()
        self._debug = self._config.get('FIX_DEBUG', debug)

        self._is_initiator = utils.Tristate(None)

        self.on_recv_msg_funcs = []
        self.on_send_msg_funcs = []

    def __aiter__(self):
        return self

    async def __anext__(self):
        msg = await self._recv_msg()
        if msg is None:
            raise StopAsyncIteration
        return msg

    @property
    def closed(self):
        return self._conn is None or self._conn.closed

    def connect(self):
        return FixConnectionContextManager(
            self._config, self._on_connect, self._on_disconnect)

    async def listen(self, reader, writer):
        conn = FixConnection(
            reader=reader,
            writer=writer,
            on_disconnect=self._on_disconnect
        )
        await self._on_connect(conn)

    async def logon(self, reset=False):
        await self._send_login(reset)

    async def logoff(self):
        msg = fix42.logoff()
        await self.send_message(msg)

    async def close(self):
        if not self.closed:
            await self._close()

    async def send_message(self, msg, skip_headers=False):
        if not skip_headers:
            seq_num = await self._store.get_seq_num()
            self._append_standard_header(msg, seq_num)
        await self._store.incr_seq_num()
        await self._store.store_message(msg)

        for func in self.on_send_msg_funcs:
            await utils.maybe_await(func, msg)

        message_sent.send(self, msg=msg)

        await self._conn.write(msg.encode())
        await self._reset_heartbeat_timer()

    def on_recv_message(self, f):
        self.on_recv_msg_funcs.append(f)
        return f

    def on_send_message(self, f):
        self.on_send_msg_funcs.append(f)
        return f

    async def _close(self):
        await self._cancel_heartbeat_timer()
        logger.info('Shutting down...')

    async def _on_connect(self, conn):
        self._conn = conn
        await self._store.store_config(self._config)

    async def _on_disconnect(self):
        await self._close()

    def _append_standard_header(
        self,
        msg,
        seq_num,
        timestamp=None
    ):
        version = self._config['FIX_VERSION']
        sender_id = self._config['FIX_SENDER_COMP_ID']
        target_id = self._config['FIX_TARGET_COMP_ID']

        pairs = (
            (self._tags.BeginString, version),
            (self._tags.SenderCompID, sender_id),
            (self._tags.TargetCompID, target_id),
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

    async def _send_heartbeat(self, test_request_id=None):
        msg = fix42.heartbeat(test_request_id)
        await self.send_message(msg)

    async def _send_test_request(self, test_request_id):
        msg = fix42.test_request(test_request_id)
        await self.send_message(msg)

    async def _send_sequence_reset(self):
        seq_num = await self._store.get_seq_num()
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

    async def _send_login(self, reset=False):

        if self._is_initiator == None:
            self._is_initiator = utils.Tristate(True)

        if self._is_initiator == False:
            self._is_initiator = utils.Tristate(None)

        login_msg = fix42.logon(
            heartbeat_interval=self._config['FIX_HEARTBEAT_INTERVAL'],
            reset_sequence=reset
        )
        await self.send_message(login_msg)

    async def _request_resend(self, start, end):
        msg = fix42.resend_request(start, end)
        await self.send_message(msg)

    async def _reset_sequence(self, new_seq_num):
        await self._store.set_remote_sequence_number(new_seq_num)
        msg = fix42.sequence_reset(new_seq_num)
        await self.send_message(msg)

    async def _resend_messages(self, start, end):
        sent_messages = await self._store.get_messages_by_seq_num(
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

    async def _recv_msg(self):
        while True:
            msg = self._parser.get_message()
            if msg:
                break
            try:
                data = await self._conn.read()
            except ConnectionError:
                break
            self._parser.append_buffer(data)
        if msg:
            await self._handle_message(msg)
        return msg

    async def _handle_message(self, msg):
        await self._store.store_message(msg, remote=True)

        for func in self.on_recv_msg_funcs:
            await utils.maybe_await(func, msg)

        message_received.send(self, msg=msg)

        try:
            await self._check_sequence_integrity(msg)
        except fe.FatalSequenceGap as error:
            if msg.is_duplicate:
                return
            elif msg.msg_type == fc.FixMsgType.Logon:
                reset_seq = msg.get(self._tags.ResetSeqNumFlag)
                is_reset = reset_seq == fc.ResetSeqNumFlag.YES
                if is_reset:
                    await self._handle_logon(msg)
            elif msg.msg_type == fc.FixMsgType.SequenceReset:
                if not self._is_gap_fill(msg):
                    await self._handle_sequence_reset(msg)
                    return
            else:
                logger.exception(error)
                await self.close()
                raise
        except fe.SequenceGap as error:

            sequence_gap.send(self, exc=error)

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
                    await self._store.set_seq_num(new_seq_num)
            return
        finally:
            await self._store.incr_seq_num(remote=True)

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
            fc.FixMsgType.Logon: self._handle_logon,
            fc.FixMsgType.TestRequest: self._handle_test_request,
            fc.FixMsgType.Reject: self._handle_reject,
            fc.FixMsgType.ResendRequest: self._handle_resend_request,
            fc.FixMsgType.SequenceReset: self._handle_sequence_reset,
        }.get(msg.msg_type)

        if handler is not None:
            await utils.maybe_await(handler, msg)

    async def _handle_logon(self, msg):
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

        reset_seq = msg.get(self._tags.ResetSeqNumFlag)
        is_reset = reset_seq == fc.ResetSeqNumFlag.YES

        if is_reset:
            await self._store.set_seq_num(1)
            await self._store.set_seq_num(1, remote=True)

        if self._is_initiator == None:
            self._is_initiator = utils.Tristate(False)
            await self._send_login(reset=is_reset)

        if self._is_initiator == True:
            self._is_initiator = utils.Tristate(None)

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
            interval = self._config['FIX_HEARTBEAT_INTERVAL']
            await asyncio.sleep(interval)
            await self._send_heartbeat()
        except asyncio.CancelledError:
            raise

    def _is_gap_fill(self, msg):
        gf_flag = msg.get(self._tags.GapFillFlag)
        return gf_flag == fc.GapFillFlag.YES
