import asyncio
from collections.abc import Coroutine
import datetime as dt
import logging

from fixation import (
    constants as fc,
    utils, exceptions, parse,
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
            if utils.is_coro(self.on_disconnect):
                await self.on_disconnect()
            else:
                self.on_disconnect()

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
                if utils.is_coro(self.on_connect):
                    await self.on_connect(conn)
                else:
                    self.on_connect(conn)
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
        if utils.is_coro(self.on_connect):
            await self.on_connect(conn)
        else:
            self.on_connect(conn)
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
        raise_on_sequence_gap=True,
        loop=None,
        debug=False
    ):
        conf = conf or config.get_config_from_env()
        config.validate_config(conf)
        self._config = conf

        self._tags = getattr(fc.FixTag, self._config['FIX_VERSION'].name)
        self._store = store or fix_store.FixRedisStore()
        self._parser = parse.FixParser(self._config)
        self._raise_on_sequence_gap = raise_on_sequence_gap
        self._fix_dict = dictionary

        self._is_resetting = False
        self._connection = None
        self._hearbeat_cb = None
        self._loop = loop or asyncio.get_event_loop()
        self._debug = self._config.get('FIX_DEBUG', debug)

        self._is_initiator = utils.Tristate(None)

    def print_msg_to_console(self, msg, remote=False):
        send_time = msg.get(self._tags.SendingTime)
        direction = '<--' if remote else '-->'
        print('{}: {} {}'.format(send_time, msg.msg_type, direction))

    def connect(self):
        self._is_initiator = utils.Tristate(True)
        return FixConnectionContextManager(
            self._config, self.on_connect, self.on_disconnect)

    def listen(self):
        self._is_initiator = utils.Tristate(False)
        return FixConnectionContextManager(
            self._config, self.on_connect, self.on_disconnect, is_server=True)

    async def on_connect(self, conn):
        self._connection = conn
        self._store.store_config(self._config)

    async def on_disconnect(self):
        await self._close()

    def append_standard_header(
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
            self.append_standard_header(
                msg, seq_num=self._store.get_seq_num())
        if self._debug:
            self.print_msg_to_console(msg)
        await self._connection.write(msg.encode())
        self._store.incr_seq_num()
        self._store.store_message(msg)
        self._reset_heartbeat_timer()

    async def send_heartbeat(self, test_request_id=None):
        msg = fix42.heartbeat(test_request_id)
        await self.send_message(msg)

    async def _send_test_request(self, test_request_id):
        msg = fix42.test_request(test_request_id)
        await self.send_message(msg)

    async def sent_sequence_reset(self):
        seq_num = self._store.get_seq_num()
        msg = fix42.sequence_reset(seq_num + 1)
        await self.send_message(msg)

    async def _send_reject(self, msg, tag, rejection_type, reason):
        ref_sequence_number = msg.seq_num
        ref_message_type = msg.msg_type
        msg = fix42.reject(
            ref_sequence_number=ref_sequence_number,
            ref_message_type=ref_message_type,
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

    async def request_resend(self, start_sequence, end_sequence):
        msg = fix42.resend_request(
            start_sequence,
            end_sequence
        )
        await self.send_message(msg)

    async def reset_sequence(self, new_sequence_number):
        self._store.set_remote_sequence_number(new_sequence_number - 1)
        msg = fix42.sequence_reset(new_sequence_number)
        await self.send_message(msg)

    async def resend_messages(self, start, end):
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
                    await self.reset_sequence(
                        new_sequence_number=gf_new_seq_num)
                    gf_seq_num, gf_new_seq_num = None, None

                msg.append_pair(
                    self._tags.PossDupFlag,
                    fc.PossDupFlag.YES,
                    header=True
                )
                await self.send_message(msg, skip_headers=True)

    def check_sequence_integrity(self, msg):
        seq_num = int(msg.get(self._tags.MsgSeqNum))
        recorded_seq_num = int(self._store.get_seq_num(remote=True))
        seq_diff = seq_num - recorded_seq_num
        if seq_diff == 0:
            return

        if seq_diff >= 1:
            raise exceptions.SequenceGap(
                msg_seq_num=seq_num,
                recorded_seq_num=recorded_seq_num
            )

        raise exceptions.FatalSequenceError(
            msg_seq_num=seq_num,
            recorded_seq_num=recorded_seq_num
        )

    async def dispatch(self, msg):
        handler = {
            fc.FixMsgType.Logon: self._handle_logon,
            fc.FixMsgType.Heartbeat: self.handle_heartbeat,
            fc.FixMsgType.TestRequest: self.handle_test_request,
            fc.FixMsgType.Reject: self.handle_reject,
            fc.FixMsgType.ResendRequest: self.handle_resend_request,
            fc.FixMsgType.SequenceReset: self.handle_sequence_reset,
        }.get(msg.msg_type)

        if handler is not None:
            if utils.is_coro(handler):
                await handler(msg)
            else:
                handler(msg)

    def is_gap_fill(self, msg):
        gf_flag = msg.get(self._tags.GapFillFlag)
        if gf_flag is None:
            return False
        gf_flag = fc.GapFillFlag(gf_flag)
        return gf_flag == fc.GapFillFlag.YES

    async def handle_message(self, msg):

        self._store.store_message(msg, remote=True)

        if self._debug:
            self.print_msg_to_console(msg, remote=True)

        if msg.msg_type == fc.FixMsgType.Logon:
            reset_seq = msg.get(self._tags.ResetSeqNumFlag)
            if reset_seq == fc.ResetSeqNumFlag.YES:
                self._store.set_seq_num(msg.seq_num, remote=True)

        if msg.msg_type == fc.FixMsgType.ResendRequest:
            await self.handle_resend_request(msg)
            return

        try:
            self.check_sequence_integrity(msg)
        except exceptions.SequenceGap as error:
            await self.request_resend(
                start_sequence=error.recorded_seq_num + 1,
                end_sequence=0
            )
            if self._raise_on_sequence_gap:
                raise
            return
        except exceptions.FatalSequenceError as error:
            logger.exception(error)
            await self.close()
            raise

        if msg.msg_type == fc.FixMsgType.SequenceReset:
            gap_fill_flag = msg.get(self._tags.GapFillFlag)
            gap_fill_flag = gap_fill_flag or fc.GapFillFlag.NO
            if gap_fill_flag == fc.GapFillFlag.NO:
                pass

            new_seq_num = int(msg.get(self._tags.NewSeqNo))
            self._store.set_seq_num(new_seq_num - 1, remote=True)

        is_resend = msg.get(self._tags.PossDupFlag) == fc.PossDupFlag.YES
        if is_resend and msg.msg_type in ADMIN_MESSAGES:
            return
        finally:
            self._store.incr_seq_num(remote=True)

        await self.dispatch(msg)

    async def handle_sequence_reset(self, msg):
        if not self.is_gap_fill(msg):
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
        if self._is_resetting:
            seq_num = int(msg.get(self._tags.MsgSeqNum))
            self._store.set_seq_num(seq_num, remote=True)
            self._is_resetting = False
        logger.debug('Login successful!')

        if self._is_initiator in (False, None):
            await self._send_login()
        if self._is_initiator is None:
            self._is_initiator = utils.Tristate(False)

    async def handle_heartbeat(self, msg):
        pass

    async def handle_resend_request(self, msg):
        start_sequence_number = int(msg.get(self._tags.BeginSeqNo))
        end_sequence_number = int(msg.get(self._tags.EndSeqNo))
        await self.resend_messages(start_sequence_number, end_sequence_number)

    async def handle_test_request(self, msg):
        test_request_id = msg.get(self._tags.TestReqID)
        await self.send_heartbeat(test_request_id=test_request_id)

    async def handle_reject(self, msg):
        reject_reason = msg.get(self._tags.Text)
        print('Reject: {}'.format(reject_reason))

    def decode_entry(self, msg):
        pass

    async def recv_msg(self):
        msg = self._parser.get_message()
        if msg:
            return msg

        while self._connection.connected:
            try:
                data = await self._connection.read()
            except ConnectionError as error:
                logger.error(error)
                break
            if data == b'':
                logger.error('Peer closed the connection!')
                break
            self._parser.append_buffer(data)
            msg = self._parser.get_message()
            if msg is not None:
                await self.handle_message(msg)
                return msg

        return None

    def _cancel_heartbeat_timer(self):
        if self._hearbeat_cb is not None:
            self._hearbeat_cb.cancel()
            self._hearbeat_cb = None

    def _reset_heartbeat_timer(self):
        self._cancel_heartbeat_timer()
        self._hearbeat_cb = self._loop.create_task(
            self.set_heartbeat_timer())

    async def set_heartbeat_timer(self):
        interval = self._config['FIX_HEARTBEAT_INTERVAL']
        try:
            await asyncio.sleep(interval)
            await self.send_heartbeat()
        except asyncio.CancelledError:
            pass
        self._reset_heartbeat_timer()

    def __aiter__(self):
        return self

    async def __anext__(self):
        msg = await self.recv_msg()
        if msg is None:
            raise StopAsyncIteration
        return msg

    async def _close(self):
        self._cancel_heartbeat_timer()
        logger.info('Shutting down...')

    async def close(self):
        await self._close()
        if self._connection.connected:
            await self._connection.close()
