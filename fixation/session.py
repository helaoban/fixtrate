import asyncio
import collections
from collections.abc import Coroutine
import datetime as dt
import logging
import sys

from . import (
    adapter, constants, message,
    utils, tags, exceptions,
    parse, store as fix_store,
    rpc
)

logging.basicConfig()
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
            constants.FixMsgType.MarketDataSnapshotFullRefresh: self.handle_market_data_full_refresh,
            constants.FixMsgType.MarketDataIncrementalRefresh: self.handle_market_data_incremental_refresh,
        }

        self.register_handlers(handlers)

    async def request_market_data(self, symbols):
        """
        Make a request for market data. Sends a Market Data Request <V>
        message.

        :param symbols: List of security symbols to subscribe to
        :return:
        """
        entry_types = [
            constants.MDEntryType.BID,
            constants.MDEntryType.OFFER,
            constants.MDEntryType.TRADE
        ]
        sequence_number = self.store.increment_local_sequence_number()
        msg = message.Message.create_market_data_request_message(
            sequence_number, self.config, symbols, entry_types
        )
        request_id = msg.get(tags.FixTag.MDReqID)

        self.store.register_symbol_request_mapping(symbols, request_id)
        await self.send_message(msg)

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
                constants.MDEntryType.OFFER,
                constants.MDEntryType.BID
            ]:
                book[tags.FixTag.MDEntryType] = {
                    'price': price,
                    'size': size
                }

            if entry_type == constants.MDEntryType.TRADE:
                trades.append({'price': price, 'size': size})

        return symbol, book, trades

    def handle_market_data_incremental_refresh(self, message):
        pass


class FixOrderEntryMixin(object):

    def __init__(self, *args, **kwargs):
        pass

    async def place_order(
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

        await self.send_message(msg)

    def handle_execution_report(self, message):
        pass


class FixConnection(object):

    def __init__(
        self,
        reader,
        writer,
        config,
        on_connect=None,
        on_disconnect=None,
        loop=None
    ):
        self.reader = reader
        self.writer = writer
        self.config = config
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect

        self.loop = loop or asyncio.get_event_loop()

        self._connected = True

    async def close(self):
        self.writer.close()
        if self.on_disconnect is not None:
            if utils.is_coro(self.on_disconnect):
                await self.on_disconnect()
            else:
                self.on_disconnect()

        self._connected = False

    async def read(self):
        return await self.reader.read(4096)

    async def write(self, *args, **kwargs):
        self.writer.write(*args, **kwargs)
        await self.writer.drain()


class FixConnectContextManager(Coroutine):

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


class FixSession(FixBaseMixin, FixMarketDataMixin, FixOrderEntryMixin, metaclass=MixedClass):
    def __init__(self, config, store=None, loop=None):
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
            constants.FixMsgType.Logon: self.handle_logon,
            constants.FixMsgType.Heartbeat: self.handle_heartbeat,
            constants.FixMsgType.TestRequest: self.handle_test_request,
            constants.FixMsgType.Reject: self.handle_reject,
            constants.FixMsgType.BusinessMessageReject: self.handle_business_message_reject,
        }

        self.register_handlers(handlers)

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
                self.on_connect()
                self._connection = FixConnection(reader, writer, self.on_disconnect)
                return self._connection

        if tries > retries:
            logger.info('Retries ({}) exhausted, shutting down.'
                        ''.format(retries))

    def connect(self):
        return FixConnectContextManager(self._connect())

    def on_connect(self):
        self._connected = True
        # self._listener = asyncio.ensure_future(self.listen())

    def on_disconnect(self):
        self._connected = False
        self.shutdown()

    async def send_message(self, msg):
        msg_type = constants.FixMsgType(msg.get(tags.FixTag.MsgType))
        seq_num = msg.get(tags.FixTag.MsgSeqNum)
        send_time = msg.get(tags.FixTag.SendingTime)

        if send_time is None:
            msg.append_utc_timestamp(
                tags.FixTag.SendingTime,
                timestamp=dt.datetime.utcnow(),
                precision=6,
                header=True
            )
            send_time = msg.get(tags.FixTag.SendingTime)

        encoded = msg.encode()
        print('{}: --> {}'.format(send_time, msg_type))
        await self._connection.write(encoded)
        self.store.store_sent_message(int(seq_num), encoded)

    async def send_heartbeat(self, test_request_id=None):
        sequence_number = self.store.increment_local_sequence_number()
        msg = message.Message.create_heartbeat_message(
            sequence_number, self.config, test_request_id
        )
        await self.send_message(msg)

    async def login(self):
        sequence_number = self.store.increment_local_sequence_number()
        login_msg = message.Message.create_login_message(
            sequence_number, self.config
        )
        # utils.print_to_console(login_msg)
        await self.send_message(login_msg)

    async def logoff(self):
        sequence_number = self.store.increment_local_sequence_number()
        msg = message.Message.create_logoff_message(
            sequence_number, self.config
        )
        await self.send_message(msg)

    async def send_test_request(self):
        sequence_number = self.store.increment_local_sequence_number()
        msg = message.Message.create_test_request_message(
            sequence_number,
            self.config
        )
        await self.send_message(msg)

    async def get_security_list(self):
        sequence_number = self.store.increment_local_sequence_number()
        msg = message.Message.create_security_list_request(
            sequence_number=sequence_number,
            config=self.config
        )
        await self.send_message(msg)

    async def request_resend(self, start_sequence, end_sequence):
        sequence_number = self.store.increment_local_sequence_number()
        msg = message.Message.create_resend_request_message(
            sequence_number=sequence_number,
            config=self.config,
            start_sequence=start_sequence,
            end_sequence=end_sequence
        )
        await self.send_message(msg)

    async def reset_sequence(self, new_sequence_number):
        sequence_number = self.store.increment_local_sequence_number()
        self.store.set_remote_sequence_number(new_sequence_number - 1)
        msg = message.Message.create_sequence_reset_message(
            sequence_number,
            self.config,
            new_sequence_number
        )
        await self.send_message(msg)

    async def resend_messages(self, start, end):
        sequence_range = range(start, end + 1)
        sent_messages = self.store.get_sent_messages()
        for seq in sequence_range:
            await self.send_message(sent_messages[seq])

    def check_sequence_integrity(self, message):
        seq_num = message.get(tags.FixTag.MsgSeqNum)
        recorded_seq_num = self.store.get_remote_sequence_number()
        seq_diff = int(seq_num) - int(recorded_seq_num)
        if seq_diff != 1:
            raise exceptions.SequenceGap

    def handle_sequence_gap(self, message):
        logger.error('Sequence GAP, resetting...')

    async def dispatch(self, message):
        msg_type = message.get(tags.FixTag.MsgType)
        try:
            msg_type = constants.FixMsgType(msg_type)
        except ValueError:
            logger.error('Unrecognized FIX message type: {}.'.format(msg_type))
            return

        handler = self._handlers.get(msg_type)
        if handler is not None:
            if utils.is_coro(handler):
                await handler(message)
            else:
                handler(message)

        # adapter = self._adapters.get(msg_type, self._default_adapter)
        # converted = adapter.dispatch(message)
        # self._out_queue.put_nowait(converted)

    async def handle_message(self, msg):
        msg_type = msg.get(tags.FixTag.MsgType)
        msg_type = constants.FixMsgType(msg_type)
        seq_num = int(msg.get(tags.FixTag.MsgSeqNum))
        send_time = msg.get(tags.FixTag.SendingTime)

        print('{}: <-- {}'.format(send_time, msg_type))

        if msg_type not in [
            constants.FixMsgType.Logon,
            constants.FixMsgType.ResendRequest
        ]:

            try:
                self.check_sequence_integrity(msg)
            except exceptions.SequenceGap:
                self.handle_sequence_gap(msg)
                return

            self.store.increment_remote_sequence_number()

        self.store.store_received_message(seq_num, msg.encode())
        await self.dispatch(msg)

    async def handle_logon(self, message):
        if self.config.reset_sequence:
            seq_num = int(message.get(tags.FixTag.MsgSeqNum))
            self.store.set_remote_sequence_number(seq_num)
        # await self.send_heartbeat()
        logger.debug('Login successful!')

    async def handle_heartbeat(self, message):
        await self.send_heartbeat()

    async def handle_resend_request(self, message):
        start_sequence_number = message.get(tags.FixTag.BeginSeqNo)
        end_sequence_number = message.get(tags.FixTag.EndSeqNo)
        await self.resend_messages(start_sequence_number, end_sequence_number)

    async def handle_test_request(self, message):
        test_request_id = message.get(tags.FixTag.TestReqID)
        await self.send_heartbeat(test_request_id=test_request_id)

    async def handle_reject(self, message):
        reject_reason = message.get(tags.FixTag.Text)
        raise exceptions.FixRejection(reason=reject_reason)

    def handle_business_message_reject(self, message):
        sequence_number = message.get(tags.FixTag.RefSeqNum)
        reject_explanation = message.get(tags.FixTag.Text)
        ref_msg_type = message.get(tags.FixTag.RefMsgType)
        business_reject_reason = message.get(tags.FixTag.BusinessRejectReason)

        handler = {
            constants.BusinessRejectReason.UNKNOWN_SECURITY: self.handle_unknown_security,
            constants.BusinessRejectReason.UNSUPPORTED_MESSAGE_TYPE: self.handle_unknown_security,
            constants.BusinessRejectReason.APPLICATION_NOT_AVAILABLE: self.handle_application_not_available,
            constants.BusinessRejectReason.CONDITIONALLY_REQUIRED_FIELD_MISSING: self.handle_missing_conditionally_required_field,
            constants.BusinessRejectReason.DELIVERTO_FIRM_NOT_AVAILABLE_AT_THIS_TIME: self.handle_deliverto_firm_not_available,
            constants.BusinessRejectReason.NOT_AUTHORIZED: self.handle_not_authorized,
            constants.BusinessRejectReason.UNKNOWN_ID: self.handle_unknown_id,
            constants.BusinessRejectReason.UNKNOWN_MESSAGE_TYPE: self.handle_unknown_message_type,
            constants.BusinessRejectReason.INVALID_PRICE_INCREMENT: self.handle_invalid_price_increment,
        }.get(business_reject_reason)

        if handler is None:
            logger.error('Handler for {} not found'
                         ''.format(business_reject_reason))
            return

        handler(message)

    async def handle_unknown_security(self):
        pass

    async def handle_unsupported_message_type(self):
        pass

    async def handle_application_not_available(self):
        pass

    async def handle_missing_conditionally_required_field(self):
        pass

    async def handle_deliverto_firm_not_available(self):
        pass

    async def handle_not_authorized(self):
        pass

    async def handle_unknown_id(self):
        pass

    async def handle_unknown_message_type(self):
        pass

    async def handle_invalid_price_increment(self):
        pass

    def decode_entry(self, message):
        pass

    # async def listen(self):
    #     parser = parse.FixParser(self.config)
    #
    #     try:
    #
    #         while self._connected:
    #             try:
    #                 data = await self._connection.read()
    #             except ConnectionError as error:
    #                 logger.error(error)
    #                 self.on_disconnect()
    #                 return
    #             if data == b'':
    #                 logger.error('Server closed the connection!')
    #                 self.on_disconnect()
    #                 return
    #             parser.append_buffer(data)
    #             msg = parser.get_message()
    #
    #             if msg is not None:
    #                 await self.handle_message(msg)
    #
    #     except asyncio.CancelledError:
    #         pass

    async def recv_msg(self):
        msg = self.parser.get_message()
        if msg:
            return msg

        while self._connected:
            try:
                data = await self._connection.read()
            except ConnectionError as error:
                logger.error(error)
                self.on_disconnect()
                return
            if data == b'':
                logger.error('Server closed the connection!')
                self.on_disconnect()
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

    def shutdown(self):
        logger.info('Shutting down...')
        if self._connected:
            self.logoff()
        self._out_queue.put_nowait(None)
        self._listener.cancel()
