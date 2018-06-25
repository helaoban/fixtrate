import asyncio
import collections
import datetime as dt
import errno
import logging
import os
import socket
import sys

from . import (
    adapter, values, message,
    utils, tags, exceptions,
    parse, store as fix_store
)


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class MixedClass(type):
    def __new__(mcs, name, bases, classdict):
        classinit = classdict.get('__init__')  # Possibly None.

        # define an __init__ function for the new class
        def __init__(self, *args, **kwargs):
            # call the __init__ functions of all the bases
            for base in type(self).__bases__:
                base.__init__(self, *args, **kwargs)
            # also call any __init__ function that was in the new class
            if classinit:
                classinit(self, *args, **kwargs)

        # add the local function to the new class
        classdict['__init__'] = __init__
        return type.__new__(mcs, name, bases, classdict)


class FixBaseMixin(object):

    def __init__(self, *args, **kwargs):
        self._adapters = {}
        self._handlers = {}

        self._default_adapter = adapter.FixAdapter()

    def register_adapter(self, tag, adapter):
        self._adapters[tag] = adapter

    def register_handlers(self, handlers):
        for msg_type, handler in handlers.items():
            self._handlers[msg_type] = handler


class FixMarketDataMixin(object):

    def __init__(self, *args, **kwargs):

        handlers = {
            values.FixValue.MsgType_MarketDataSnapshotFullRefresh: self.handle_market_data_full_refresh,
            values.FixValue.MsgType_MarketDataIncrementalRefresh: self.handle_market_data_incremental_refresh,
        }

        self.register_handlers(handlers)

    def request_market_data(self, symbols):
        """
        Make a request for market data. Sends a Market Data Request <V>
        message.

        :param symbols: List of security symbols to subscribe to
        :return:
        """
        entry_types = [
            values.FixValue.MDEntryType_BID,
            values.FixValue.MDEntryType_OFFER,
            values.FixValue.MDEntryType_TRADE
        ]
        sequence_number = self.store.increment_local_sequence_number()
        msg = message.Message.create_market_data_request_message(
            sequence_number, self.config, symbols, entry_types
        )
        request_id = msg.get(tags.FixTag.MDReqID)

        self.store.register_symbol_request_mapping(symbols, request_id)
        self.send_message(msg)

    def handle_market_data_full_refresh(self, message):
        market_request_id = message.get(262)
        if market_request_id is None:
            return
        symbol = message.get(55)
        number_of_entries = message.get(268)

        book = collections.defaultdict(list)
        trades = []
        for i in range(number_of_entries):
            entry_type = message.get(tags.FixTag.MDEntryType)
            price = message.get(tags.FixTag.MDEntryPx)
            size = message.get(tags.FixTag.MDEntrySize)

            if entry_type in [
                values.FixValue.MDEntryType_OFFER,
                values.FixValue.MDEntryType_BID
            ]:
                book[tags.FixTag.MDEntryType] = {
                    'price': price,
                    'size': size
                }

            if entry_type == values.FixValue.MDEntryType_TRADE:
                trades.append({'price': price, 'size': size})

        return symbol, book, trades

    def handle_market_data_incremental_refresh(self, message):
        pass


class FixOrderEntryMixin(object):

    def __init__(self, *args, **kwargs):
        pass

    def place_order(
        self,
        symbol,
        side,
        order_type,
        quantity,
        price=None
    ):

        order_types = ['limit']
        if order_type not in order_types:
            raise ValueError("Invalid order type '{}'".format(order_type))

        order_sides = ['buy, sell']
        if side not in order_sides:
            raise ValueError("Invalid order side '{}'".format(side))

        if order_type == 'limit':
            if price is None:
                raise ValueError('Price must be specified for {} orders'
                                 ''.format(order_type))

        sequence_number = self.store.increment_local_sequence_number()
        msg = message.Message.create_new_order_message(
            sequence_number=sequence_number,
            config=self.config,
            symbol=symbol,
            order_type=order_type,
            side=side,
            quantity=quantity,
            price=price
        )

        self.send_message(msg)

    def handle_execution_report(self, message):
        pass


class FixConnection(object):

    def __init__(
        self,
        config,
        on_connect=None,
        on_disconnect=None,
        loop=None
    ):
        self.config = config

        self.on_connect = on_connect
        self.on_disconnect = on_disconnect

        self._writer = None
        self._reader = None

        self.loop = loop or asyncio.get_event_loop()

    async def __aenter__(self):
        try:
            await self.connect()
        except Exception:
            if await self.__aexit__(*sys.exc_info()):
                pass
            else:
                raise

    async def __aexit__(self, exc_type, exc, tb):
        await self.disconnect()

    async def connect(self, retries=5, retry_wait=1):
        tries = 0
        while tries <= retries:
            try:
                self._reader, self._writer = await asyncio.open_connection(
                    host=self.config.host,
                    port=self.config.port,
                    loop=self.loop
                )
            except OSError as error:
                logger.error(error)
                logger.info('Connection failed, retrying in 5 seconds...')
                tries += 1
                await asyncio.sleep(retry_wait)
                continue
            else:
                if self.on_connect is not None:
                    if utils.is_coro(self.on_connect):
                        await self.on_connect()
                    else:
                        self.on_connect()
                break

        if tries > retries:
            logger.info('Retries ({}) exhausted, shutting down.'
                        ''.format(retries))

    async def disconnect(self):
        self._writer.close()
        if self.on_disconnect is not None:
            if utils.is_coro(self.on_disconnect):
                await self.on_disconnect()
            else:
                self.on_disconnect()

    async def read(self, *args, **kwargs):
        return await self._reader.read(*args, **kwargs)

    async def write(self, *args, **kwargs):
        self._writer.write(*args, **kwargs)
        await self._writer.drain()


class FixSession(FixBaseMixin, FixMarketDataMixin, FixOrderEntryMixin, metaclass=MixedClass):
    def __init__(
            self,
            config,
            store=None,
            loop=None,
    ):
        config.validate()
        self.config = config
        self.config_path = '~/.fixation'
        self.loop = loop or asyncio.get_event_loop()
        self.store = store or fix_store.FixRedisStore()
        self.reader = None
        self.writer = None
        self._connected = True
        self._connection = None
        self._listener = None
        self._socket_server = None
        self._closing = False

        self._out_queue = asyncio.Queue()

        handlers = {
            values.FixValue.MsgType_Logon: self.handle_login,
            values.FixValue.MsgType_Heartbeat: self.handle_heartbeat,
            values.FixValue.MsgType_TestRequest: self.handle_test_request,
            values.FixValue.MsgType_Reject: self.handle_reject,
            values.FixValue.MsgType_BusinessMessageReject: self.handle_business_message_reject,
        }

        self.register_handlers(handlers)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        pass

    async def send_message(self, msg):
        seq_num = msg.get(tags.FixTag.MsgSeqNum)
        send_time = msg.get(tags.FixTag.SendingTime)

        if send_time is None:
            msg.append_utc_timestamp(
                tags.FixTag.SendingTime,
                timestamp=dt.datetime.utcnow(),
                precision=6,
                header=True
            )

        encoded = msg.encode()
        print(encoded)
        await self._connection.write(encoded)
        self.store.store_sent_message(int(seq_num), encoded)

    def send_heartbeat(self, test_request_id=None):
        sequence_number = self.store.increment_local_sequence_number()
        msg = message.Message.create_heartbeat_message(
            sequence_number, self.config, test_request_id
        )
        self.send_message(msg)

    async def login(self):
        sequence_number = self.store.increment_local_sequence_number()
        login_msg = message.Message.create_login_message(
            sequence_number, self.config
        )
        await self.send_message(login_msg)

    def logoff(self):
        sequence_number = self.store.increment_local_sequence_number()
        msg = message.Message.create_logoff_message(
            sequence_number, self.config
        )
        self.send_message(msg)

    def send_test_request(self):
        sequence_number = self.store.increment_local_sequence_number()
        msg = message.Message.create_test_request_message(
            sequence_number,
            self.config
        )
        self.send_message(msg)

    def get_security_list(self):
        sequence_number = self.store.increment_local_sequence_number()
        msg = message.Message.create_security_list_request(
            sequence_number=sequence_number,
            config=self.config
        )
        self.send_message(msg)

    def request_resend(self, start_sequence, end_sequence):
        sequence_number = self.store.increment_local_sequence_number()
        msg = message.Message.create_resend_request_message(
            sequence_number=sequence_number,
            config=self.config,
            start_sequence=start_sequence,
            end_sequence=end_sequence
        )
        self.send_message(msg)

    def reset_sequence(self, new_sequence_number):
        sequence_number = self.store.increment_local_sequence_number()
        self.store.set_remote_sequence_number(new_sequence_number - 1)
        msg = message.Message.create_sequence_reset_message(
            sequence_number,
            self.config,
            new_sequence_number
        )
        self.send_message(msg)

    def resend_messages(self, start, end):
        sequence_range = range(start, end + 1)
        sent_messages = self.store.get_sent_messages()
        for seq in sequence_range:
            self.send_message(sent_messages[seq])

    async def handle_message(self, msg):
        msg_type = values.FixValue(msg.get(tags.FixTag.MsgType))
        seq_num = int(msg.get(tags.FixTag.MsgSeqNum.value))

        if msg_type not in [
            values.FixValue.MsgType_Logon,
            values.FixValue.MsgType_ResendRequest
        ]:

            try:
                self.check_sequence_integrity(msg)
            except exceptions.SequenceGap:
                logger.error('Sequence GAP, resetting...')
                self.handle_sequence_gap(msg)
                return

            self.store.increment_remote_sequence_number()

        self.store.store_received_message(seq_num, msg.encode())
        self.dispatch(msg)

    def check_sequence_integrity(self, message):
        seq_num = message.get(tags.FixTag.MsgSeqNum)
        recorded_seq_num = self.store.get_remote_sequence_number()
        seq_diff = int(seq_num) - int(recorded_seq_num)
        if seq_diff != 1:
            raise exceptions.SequenceGap

    def handle_sequence_gap(self, message):
        pass

    def dispatch(self, message):

        msg_type = message.get(tags.FixTag.MsgType)
        logger.debug('Fix message received: {}'.format(msg_type))

        try:
            msg_type = values.FixValue(msg_type)
        except ValueError:
            logger.error('Unrecognized FIX value {}.'.format(msg_type))
            return

        handler = self._handlers.get(msg_type)
        if handler is not None:
            handler(message)

        adapter = self._adapters.get(msg_type, self._default_adapter)
        converted = adapter.dispatch(message)
        self._out_queue.put_nowait(converted)

    def handle_login(self, message):
        if self.config.reset_sequence:
            seq_num = int(message.get(tags.FixTag.MsgSeqNum))
            self.store.set_remote_sequence_number(seq_num)

        self.send_heartbeat()
        logger.debug('Login successful!')

    def handle_heartbeat(self, message):
        pass

    def handle_resend_request(self, message):
        start_sequence_number = message.get(tags.FixTag.BeginSeqNo)
        end_sequence_number = message.get(tags.FixTag.EndSeqNo)
        self.resend_messages(start_sequence_number, end_sequence_number)

    def handle_test_request(self, message):
        test_request_id = message.get(tags.FixTag.TestReqID)
        self.send_heartbeat(test_request_id=test_request_id)

    def handle_reject(self, message):
        reject_reason = message.get(tags.FixTag.Text)
        raise exceptions.FixRejection(reason=reject_reason)

    def handle_business_message_reject(self, message):
        sequence_number = message.get(tags.FixTag.RefSeqNum)
        reject_explanation = message.get(tags.FixTag.Text)
        ref_msg_type = message.get(tags.FixTag.RefMsgType)
        business_reject_reason = message.get(tags.FixTag.BusinessRejectReason)

        handler = {
            values.FixValue.BusinessRejectReason_UNKNOWN_SECURITY: self.handle_unknown_security,
            values.FixValue.BusinessRejectReason_UNSUPPORTED_MESSAGE_TYPE: self.handle_unknown_security,
            values.FixValue.BusinessRejectReason_APPLICATION_NOT_AVAILABLE: self.handle_application_not_available,
            values.FixValue.BusinessRejectReason_CONDITIONALLY_REQUIRED_FIELD_MISSING: self.handle_missing_conditionally_required_field,
            values.FixValue.BusinessRejectReason_DELIVERTO_FIRM_NOT_AVAILABLE_AT_THIS_TIME: self.handle_deliverto_firm_not_available,
            values.FixValue.BusinessRejectReason_NOT_AUTHORIZED: self.handle_not_authorized,
            values.FixValue.BusinessRejectReason_UNKNOWN_ID: self.handle_unknown_id,
            values.FixValue.BusinessRejectReason_UNKNOWN_MESSAGE_TYPE: self.handle_unknown_message_type,
            values.FixValue.BusinessRejectReason_INVALID_PRICE_INCREMENT: self.handle_invalid_price_increment,
        }.get(business_reject_reason)

        if handler is None:
            logger.error('Handler for {} not found'
                         ''.format(business_reject_reason))
            return

        handler(message)

    def handle_unknown_security(self):
        pass

    def handle_unsupported_message_type(self):
        pass

    def handle_application_not_available(self):
        pass

    def handle_missing_conditionally_required_field(self):
        pass

    def handle_deliverto_firm_not_available(self):
        pass

    def handle_not_authorized(self):
        pass

    def handle_unknown_id(self):
        pass

    def handle_unknown_message_type(self):
        pass

    def handle_invalid_price_increment(self):
        pass

    def decode_entry(self, message):
        pass

    def connect(self):
        self._connection = FixConnection(
            self.config,
            on_connect=self.on_connected,
            on_disconnect=self.on_disconnected
        )
        return self._connection

    def on_connected(self):
        self._connected = True
        self._listener = asyncio.ensure_future(self.listen())
        self.start_socket_server()

    def on_disconnected(self):
        self._connected = False
        self.shutdown()

    async def listen(self):
        parser = parse.FixParser(self.config)

        try:

            while self._connected:
                try:
                    data = await self._connection.read(100)
                except ConnectionError as error:
                    logger.error(error)
                    self.on_disconnected()
                if len(data) == 0:
                    logger.error('Server closed the connection!')
                    self.on_disconnected()
                    return
                parser.append_buffer(data)
                msg = parser.get_message()
                print(msg)

                if msg is not None:
                    await self.handle_message(msg)

        except asyncio.CancelledError:
            pass

    def make_config_dir(self):
        path = os.path.expanduser(self.config_path)
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except OSError as error:
                if error.errno != errno.EEXIST:
                    raise
        return path

    def make_socket_file(self):
        config_dir = self.make_config_dir()
        path = os.path.join(config_dir, 'command_socket')

        try:
            os.remove(path)
        except OSError:
            pass

        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.bind(path)

        return path

    def start_socket_server(self):
        socket_path = self.make_socket_file()
        socket_coro = asyncio.start_unix_server(
            self.handle_socket_client,
            path=socket_path,
            loop=self.loop
        )
        self._socket_server = asyncio.ensure_future(socket_coro)

    def mock_send_test_request(self, **kwargs):
        return {'response': 'test request successful'}

    async def handle_socket_command(self, name, **kwargs):

        handler = {
            'place_order': self.place_order,
            'send_test_request': self.mock_send_test_request
        }.get(name)

        if handler:
            return handler(**kwargs)

        raise exceptions.UnknownCommand

    @staticmethod
    def parse_socket_command(data):

        lines = data.splitlines()
        name = lines[0]
        # remove 'done'
        arg_lines = lines[1: len(lines) - 1]

        kwargs = {}
        for line in arg_lines:
            items = line.split('\t')
            key = items[0]
            value = items[1:]

            if len(value) < 2:
                value = items[1]

            kwargs[key] = value

        return name, kwargs

    @staticmethod
    def validate_socket_command(data, args):
        return True

    async def handle_socket_client(self, reader, writer, timeout=10):
        print('client connected')
        buf = b''
        while True:
            try:
                buf += await asyncio.wait_for(reader.read(4096), timeout)
            except asyncio.TimeoutError:
                print('Timeout error!')
                writer.write(b'Timeout!')
                writer.close()
                return

            if buf == b'':
                print('client disconnected')
                return

            if b'done\n' in buf:
                break

        data = buf.decode()

        try:
            name, kwargs = self.parse_socket_command(data)
        except Exception as error:
            print(error)
            writer.write(b'error')
            return

        try:
            self.validate_socket_command(name, kwargs)
        except Exception as error:
            print(error)
            writer.write(b'error')
            return

        writer.write(b'ok\n')

        try:
            r = await self.handle_socket_command(name, **kwargs)
        except exceptions.UnknownCommand:
            writer.write(b'error\n')
            return
        except Exception as error:
            print(error)
            writer.write(b'error\n')
            return

        lines = []
        for k, v in r.items():
            if hasattr(v, '__iter__') and not isinstance(v, str):
                v = list(v)
            else:
                v = [v]

            line = '{}\n'.format('\t'.join([k, *v]))
            lines.append(line.encode())

        lines.append(b'done\n')
        writer.writelines(lines)

    def shutdown(self):
        logger.info('Shutting down...')
        if self._connected:
            self.logoff()
        self._out_queue.put_nowait(None)
        self._listener.cancel()
        self._socket_server.cancel()

    def __aiter__(self):
        return self

    async def __anext__(self):
        msg = await self._out_queue.get()
        if msg is None:
            raise StopAsyncIteration
        return msg

    def __call__(self, *args, **kwargs):

        socket_coro = asyncio.start_unix_server(
            self.handle_socket_client,
            path=os.path.expanduser(
                '~/.fixation/command_socket'
            ),
            loop=self.loop
        )

        socket_server = self.loop.create_task(socket_coro)
        self.loop.run_until_complete(self.connect())
        self.loop.run_until_complete(self.listen())

        socket_server.cancel()
        self.loop.run_until_complete(socket_server)
        self.loop.close()
