import asyncio
import collections
import logging

from fixation import (
    constants as fc, session,
    config, store
)
from fixation.factories import fix42


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class FixClient(object):

    def __init__(self, conf=None):
        self.session = None

        if conf is None:
            conf = config.get_config_from_env()
        else:
            config.validate_config(conf)
        self.config = conf

        self.loop = asyncio.get_event_loop()
        self._handlers = {}

        handlers = {
            fc.FixMsgType.MarketDataSnapshotFullRefresh: self.handle_market_data_full_refresh,
            fc.FixMsgType.MarketDataIncrementalRefresh: self.handle_market_data_incremental_refresh,
        }

        self.register_handlers(handlers)

        self.TAGS = self.TAGS.FIX42

    def register_handlers(self, handlers):
        for msg_type, handler in handlers.items():
            self._handlers[msg_type] = handler

    async def send_message(self, msg):
        self.append_standard_headers(msg)
        await self.session.send_message(msg)

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

        msg_type = msg.get(self.TAGS.MsgType)

        msg.append_pair(
            self.TAGS.BeginString,
            self.config['FIX_VERSION'],
            header=True
        )
        msg.append_pair(
            self.TAGS.MsgType,
            msg_type,
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

        if timestamp is not None:
            msg.append_utc_timestamp(
                self.TAGS.SendingTime,
                timestamp=timestamp,
                precision=6,
                header=True
            )

    async def get_security_list(self):
        msg = fix42.security_list()
        await self.session.send_message(msg)

    async def request_market_data(self, symbols):
        """
        Make a request for market data. Sends a Market Data Request <V>
        message.

        :param symbols: List of security symbols to subscribe to
        :return:
        """
        entry_types = [
            fc.MDEntryType.BID,
            fc.MDEntryType.OFFER,
            fc.MDEntryType.TRADE
        ]

        msg = fix42.market_data_request(
            symbols, entry_types
        )
        await self.session.send_message(msg)

    def handle_market_data_full_refresh(self, msg):
        market_request_id = msg.get(262)
        if market_request_id is None:
            return
        symbol = msg.get(55)
        number_of_entries = msg.get(268)

        book = collections.defaultdict(list)
        trades = []
        for i in range(number_of_entries):
            entry_type = msg.get(self.TAGS.MDEntryType)
            price = msg.get(self.TAGS.MDEntryPx)
            size = msg.get(self.TAGS.MDEntrySize)

            if entry_type in [
                fc.MDEntryType.OFFER,
                fc.MDEntryType.BID
            ]:
                book[self.TAGS.MDEntryType] = {
                    'price': price,
                    'size': size
                }

            if entry_type == fc.MDEntryType.TRADE:
                trades.append({'price': price, 'size': size})

        return symbol, book, trades

    def handle_market_data_incremental_refresh(self, msg):
        pass

    async def listen(self):
        self.session = session.FixSession(
            conf=self.config,
            loop=self.loop,
            store=store.FixMemoryStore()
        )

        try:

            async with self.session.connect() as conn:
                await self.session.logon()
                async for msg in self.session:
                    print(msg)

        except asyncio.CancelledError:
            print('DONE YO')

    async def place_order(
        self,
        symbol,
        side,
        order_type,
        quantity,
        price=None
    ):

        if order_type not in fc.OrdType:
            self.raise_invalid_option('order_type', fc.OrdType)

        if side not in fc.Side:
            self.raise_invalid_option('side', fc.Side)

        if order_type is fc.OrdType.LIMIT:
            if price is None:
                raise ValueError('Price must be specified for {} orders'
                                 ''.format(order_type))

        msg = fix42.new_order(
            symbol=symbol,
            order_type=order_type,
            side=side,
            quantity=quantity,
            price=price
        )

        await self.session.send_message(msg)

    def handle_execution_report(self, msg):
        pass

    def handle_business_message_reject(self, msg):
        sequence_number = msg.get(self.TAGS.RefSeqNum)
        reject_explanation = msg.get(self.TAGS.Text)
        ref_msg_type = msg.get(self.TAGS.RefMsgType)
        business_reject_reason = msg.get(
            self.TAGS.BusinessRejectReason)

        handler = {
            fc.BusinessRejectReason.UNKNOWN_SECURITY: self.handle_unknown_security,
            fc.BusinessRejectReason.UNSUPPORTED_MESSAGE_TYPE: self.handle_unknown_security,
            fc.BusinessRejectReason.APPLICATION_NOT_AVAILABLE: self.handle_application_not_available,
            fc.BusinessRejectReason.CONDITIONALLY_REQUIRED_FIELD_MISSING: self.handle_missing_conditionally_required_field,
            fc.BusinessRejectReason.DELIVERTO_FIRM_NOT_AVAILABLE_AT_THIS_TIME: self.handle_deliverto_firm_not_available,
            fc.BusinessRejectReason.NOT_AUTHORIZED: self.handle_not_authorized,
            fc.BusinessRejectReason.UNKNOWN_ID: self.handle_unknown_id,
            fc.BusinessRejectReason.UNKNOWN_MESSAGE_TYPE: self.handle_unknown_message_type,
            fc.BusinessRejectReason.INVALID_PRICE_INCREMENT: self.handle_invalid_price_increment,
        }.get(business_reject_reason)

        if handler is None:
            logger.error('Handler for {} not found'
                         ''.format(business_reject_reason))
            return

        handler(msg)

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

    def __call__(self):
        listener = self.loop.create_task(self.listen())
        try:
            self.loop.run_until_complete(listener)
        except (SystemExit, KeyboardInterrupt):
            listener.cancel()
            self.loop.run_until_complete(listener)

    def raise_invalid_option(self, name, valid_options):
        raise ValueError(
            '{} must be one of: {}'
            ''.format(name, self.list_options(valid_options))
        )

    @staticmethod
    def list_options(options):
        return '|'.join(o for o in options)
