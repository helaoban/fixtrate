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
        loop=None
    ):
        self.config = conf
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.loop = loop or asyncio.get_event_loop()

        self._coro = self._connect()

    async def _connect(self, retries=5, retry_wait=5):
        tries = 1
        while tries <= retries:
            try:
                reader, writer = await asyncio.open_connection(
                    host=self.config.get('FIX_HOST', '127.0.0.1'),
                    port=self.config.get('FIX_PORT', 4000),
                    loop=self.loop
                )
            except OSError as error:
                logger.error(error)
                logger.info('Connection failed, retrying in {} seconds...'
                            ''.format(retry_wait))
                tries += 1
                await asyncio.sleep(retry_wait)
                continue
            else:
                conn = FixConnection(
                    reader, writer, self.on_disconnect)
                self.on_connect(conn)
                return conn

        logger.info('Retries ({}) exhausted'.format(retries))
        raise ConnectionError

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
    def __init__(
        self,
        conf=None,
        store=None,
        loop=None,
        dictionary=None
    ):

        if conf is None:
            conf = config.get_config_from_env()
        else:
            config.validate_config(conf)
        self.config = conf

        self.loop = loop or asyncio.get_event_loop()
        self.store = store or fix_store.FixRedisStore()
        self.reader = None
        self.writer = None
        self._connected = True
        self._connection = None
        self._closing = False

        self.parser = parse.FixParser(self.config)

        self.TAGS = getattr(fc.FixTag, self.config['FIX_VERSION'].name)

        self._is_resetting = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        pass

    def connect(self):
        return FixConnectionContextManager(
            self.config, self.on_connect, self.on_disconnect)

    def on_connect(self, conn):
        self._connection = conn
        self.store.store_config(self.config)

    async def on_disconnect(self):
        await self.shutdown()

    def append_standard_header(
        self,
        msg,
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
            self.TAGS.BeginString,
            self.config['FIX_VERSION'],
            header=True
        )
        msg.append_pair(
            self.TAGS.SenderCompID,
            self.config['FIX_SENDER_COMP_ID'],
            header=True
        )
        msg.append_pair(
            self.TAGS.TargetCompID,
            self.config['FIX_TARGET_COMP_ID'],
            header=True
        )
        msg.append_pair(
            self.TAGS.MsgSeqNum,
            self.store.incr_seq_num()
        )

        if timestamp is None:
            timestamp = dt.datetime.utcnow()

        msg.append_utc_timestamp(
            self.TAGS.SendingTime,
            timestamp=timestamp,
            precision=6,
            header=True
        )

    async def send_message(self, msg):
        self.append_standard_header(msg)
        msg_type = fc.FixMsgType(msg.get(
            self.TAGS.MsgType))
        send_time = msg.get(self.TAGS.SendingTime)
        encoded = msg.encode()
        print('{}: {} -->'.format(send_time, msg_type))
        await self._connection.write(encoded)
        self.store.store_message(msg)

    async def send_heartbeat(self, test_request_id=None):
        msg = fix42.heartbeat(test_request_id)
        await self.send_message(msg)

    async def logon(self):
        """
        Send a Logon <A> message. Note: setting reset_sequence=True will
        set the ResetSeqNumFlag to 'Y', which for most counter-parties
        means opening new FIX session, and so we clear the store.

        :return:
        """
        self._is_resetting = self.config['FIX_RESET_SEQUENCE']
        if self._is_resetting:
            self.store.new_session()

        login_msg = fix42.logon(
            heartbeat_interval=self.config['FIX_HEARTBEAT_INTERVAL'],
            reset_sequence=self._is_resetting
        )
        await self.send_message(login_msg)

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
        self.store.set_remote_sequence_number(new_sequence_number - 1)
        msg = fix42.sequence_reset(new_sequence_number)
        await self.send_message(msg)

    async def resend_messages(self, start, end):
        sequence_range = range(start, end + 1)
        sent_messages = self.store.get_messages_by_seq_num(remote=False)
        for i in sequence_range:
            await self.send_message(sent_messages[i])

    def check_sequence_integrity(self, msg):
        seq_num = msg.get(self.TAGS.MsgSeqNum)
        recorded_seq_num = self.store.get_seq_num(remote=True)
        seq_diff = int(seq_num) - int(recorded_seq_num)
        if seq_diff != 1:
            raise exceptions.SequenceGap

    def handle_sequence_gap(self, msg):
        logger.error('Sequence GAP, resetting...')

    async def dispatch(self, msg):
        msg_type = msg.get(self.TAGS.MsgType)
        try:
            msg_type = fc.FixMsgType(msg_type)
        except ValueError:
            logger.error('Unrecognized FIX message type: {}.'.format(msg_type))
            return

        handler = {
            fc.FixMsgType.Logon: self.handle_logon,
            fc.FixMsgType.Heartbeat: self.handle_heartbeat,
            fc.FixMsgType.TestRequest: self.handle_test_request,
            fc.FixMsgType.Reject: self.handle_reject,
        }.get(msg_type)

        if handler is not None:
            if utils.is_coro(handler):
                await handler(msg)
            else:
                handler(msg)

    async def handle_message(self, msg):
        msg_type = msg.get(self.TAGS.MsgType)
        msg_type = fc.FixMsgType(msg_type)
        send_time = msg.get(self.TAGS.SendingTime)

        print('{}: {} <--'.format(send_time, msg_type))

        if msg_type not in [
            fc.FixMsgType.Logon,
            fc.FixMsgType.ResendRequest,
            fc.FixMsgType.Reject
        ]:

            try:
                self.check_sequence_integrity(msg)
            except exceptions.SequenceGap:
                self.handle_sequence_gap(msg)

            self.store.incr_seq_num(remote=True)

        self.store.store_message(msg, remote=True)
        await self.dispatch(msg)

    async def handle_logon(self, msg):
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
            seq_num = int(msg.get(self.TAGS.MsgSeqNum))
            self.store.set_seq_num(seq_num, remote=True)
            self._is_resetting = False
        logger.debug('Login successful!')

    async def handle_heartbeat(self, msg):
        await self.send_heartbeat()

    async def handle_resend_request(self, msg):
        start_sequence_number = msg.get(self.TAGS.BeginSeqNo)
        end_sequence_number = msg.get(self.TAGS.EndSeqNo)
        await self.resend_messages(start_sequence_number, end_sequence_number)

    async def handle_test_request(self, msg):
        test_request_id = msg.get(self.TAGS.TestReqID)
        await self.send_heartbeat(test_request_id=test_request_id)

    async def handle_reject(self, msg):
        reject_reason = msg.get(self.TAGS.Text)
        raise exceptions.FixRejection(reason=reject_reason)

    def decode_entry(self, msg):
        pass

    async def recv_msg(self):
        msg = self.parser.get_message()
        if msg:
            return msg

        while self._connection.connected:
            try:
                data = await self._connection.read()
            except ConnectionError as error:
                logger.error(error)
                break
            if data == b'':
                logger.error('Server closed the connection!')
                break
            self.parser.append_buffer(data)
            msg = self.parser.get_message()

            if msg is not None:
                await self.handle_message(msg)
                return msg

        return None

    def __aiter__(self):
        return self

    async def __anext__(self):
        msg = await self.recv_msg()
        if msg is None:
            raise StopAsyncIteration
        return msg

    async def shutdown(self):
        logger.info('Shutting down...')
        if self._connection.connected:
            await self.logoff()
