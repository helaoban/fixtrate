import asyncio
from collections.abc import Coroutine
import datetime as dt
import logging

from fixation import (
    constants, message as fm,
    utils, exceptions, parse,
    store as fix_store, config
)

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

    def __init__(self, coro):
        self._coro = coro

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
        self._conn.close()


class FixSession:
    def __init__(self, conf=None, store=None, loop=None):

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

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        pass

    async def _connect(self, retries=5, retry_wait=1):
        tries = 0
        while tries <= retries:
            try:
                reader, writer = await asyncio.open_connection(
                    host=self.config.get('FIX_HOST', '127.0.0.1'),
                    port=self.config.get('FIX_PORT', 4000),
                    loop=self.loop
                )
            except OSError as error:
                logger.error(error)
                logger.info('Connection failed, retrying in 5 seconds...')
                tries += 1
                await asyncio.sleep(retry_wait)
                continue
            else:
                self.on_connect()
                self._connection = FixConnection(
                    reader, writer, self.on_disconnect)
                return self._connection

        if tries > retries:
            logger.info('Retries ({}) exhausted, shutting down.'
                        ''.format(retries))

    def connect(self):
        return FixConnectionContextManager(self._connect())

    def on_connect(self):
        pass

    async def on_disconnect(self):
        await self.shutdown()

    def append_standard_headers(
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
            constants.FixTag.BeginString,
            self.config['FIX_VERSION'],
            header=True
        )
        msg.append_pair(
            constants.FixTag.SenderCompID,
            self.config['FIX_SENDER_COMP_ID'],
            header=True
        )
        msg.append_pair(
            constants.FixTag.TargetCompID,
            self.config['FIX_TARGET_COMP_ID'],
            header=True
        )
        msg.append_pair(
            constants.FixTag.MsgSeqNum,
            self.store.increment_local_sequence_number()
        )

        if timestamp is None:
            timestamp = dt.datetime.utcnow()

        msg.append_utc_timestamp(
            constants.FixTag.SendingTime,
            timestamp=timestamp,
            precision=6,
            header=True
        )

    async def send_message(self, msg):
        self.append_standard_headers(msg)
        msg_type = constants.FixMsgType(msg.get(
            constants.FixTag.MsgType))
        seq_num = msg.get(constants.FixTag.MsgSeqNum)
        send_time = msg.get(constants.FixTag.SendingTime)
        encoded = msg.encode()
        print('{}: --> {}'.format(send_time, msg_type))
        await self._connection.write(encoded)
        self.store.store_sent_message(int(seq_num), encoded)

    async def send_heartbeat(self, test_request_id=None):
        msg = fm.FixMessage.create_heartbeat_message(test_request_id)
        await self.send_message(msg)

    async def login(self):
        login_msg = fm.FixMessage.create_login_message()
        await self.send_message(login_msg)

    async def logoff(self):
        msg = fm.FixMessage.create_logoff_message()
        await self.send_message(msg)

    async def send_test_request(self):
        msg = fm.FixMessage.create_test_request_message()
        await self.send_message(msg)

    async def request_resend(self, start_sequence, end_sequence):
        msg = fm.FixMessage.create_resend_request_message(
            start_sequence,
            end_sequence
        )
        await self.send_message(msg)

    async def reset_sequence(self, new_sequence_number):
        self.store.set_remote_sequence_number(new_sequence_number - 1)
        msg = fm.FixMessage.create_sequence_reset_message(new_sequence_number)
        await self.send_message(msg)

    async def resend_messages(self, start, end):
        sequence_range = range(start, end + 1)
        sent_messages = self.store.get_sent_messages()
        for seq in sequence_range:
            await self.send_message(sent_messages[seq])

    def check_sequence_integrity(self, msg):
        seq_num = msg.get(constants.FixTag.MsgSeqNum)
        recorded_seq_num = self.store.get_remote_sequence_number()
        seq_diff = int(seq_num) - int(recorded_seq_num)
        if seq_diff != 1:
            raise exceptions.SequenceGap

    def handle_sequence_gap(self, msg):
        logger.error('Sequence GAP, resetting...')

    async def dispatch(self, msg):
        msg_type = msg.get(constants.FixTag.MsgType)
        try:
            msg_type = constants.FixMsgType(msg_type)
        except ValueError:
            logger.error('Unrecognized FIX message type: {}.'.format(msg_type))
            return

        handler = {
            constants.FixMsgType.Logon: self.handle_logon,
            constants.FixMsgType.Heartbeat: self.handle_heartbeat,
            constants.FixMsgType.TestRequest: self.handle_test_request,
            constants.FixMsgType.Reject: self.handle_reject,
        }.get(msg_type)

        if handler is not None:
            if utils.is_coro(handler):
                await handler(msg)
            else:
                handler(msg)

    async def handle_message(self, msg):
        msg_type = msg.get(constants.FixTag.MsgType)
        msg_type = constants.FixMsgType(msg_type)
        seq_num = int(msg.get(constants.FixTag.MsgSeqNum))
        send_time = msg.get(constants.FixTag.SendingTime)

        print('{}: <-- {}'.format(send_time, msg_type))

        if msg_type not in [
            constants.FixMsgType.Logon,
            constants.FixMsgType.ResendRequest,
            constants.FixMsgType.Reject
        ]:

            try:
                self.check_sequence_integrity(msg)
            except exceptions.SequenceGap:
                self.handle_sequence_gap(msg)

            self.store.increment_remote_sequence_number()

        self.store.store_received_message(seq_num, msg.encode())
        await self.dispatch(msg)

    async def handle_logon(self, msg):
        if self.config.get('FIX_RESET_SEQUENCE'):
            seq_num = int(msg.get(constants.FixTag.MsgSeqNum))
            self.store.set_remote_sequence_number(seq_num)
        logger.debug('Login successful!')

    async def handle_heartbeat(self, msg):
        await self.send_heartbeat()

    async def handle_resend_request(self, msg):
        start_sequence_number = msg.get(constants.FixTag.BeginSeqNo)
        end_sequence_number = msg.get(constants.FixTag.EndSeqNo)
        await self.resend_messages(start_sequence_number, end_sequence_number)

    async def handle_test_request(self, msg):
        test_request_id = msg.get(constants.FixTag.TestReqID)
        await self.send_heartbeat(test_request_id=test_request_id)

    async def handle_reject(self, msg):
        reject_reason = msg.get(constants.FixTag.Text)
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
                await self.on_disconnect()
                return
            if data == b'':
                logger.error('Server closed the connection!')
                await self.on_disconnect()
                return
            self.parser.append_buffer(data)
            msg = self.parser.get_message()

            if msg is not None:
                await self.handle_message(msg)
                return msg

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
