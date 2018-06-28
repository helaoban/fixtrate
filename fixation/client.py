import asyncio
import collections
import logging

import fixation.constants
from fixation import (
    constants, session,
    config, message,
    store
)


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
            constants.FixMsgType.MarketDataSnapshotFullRefresh: self.handle_market_data_full_refresh,
            constants.FixMsgType.MarketDataIncrementalRefresh: self.handle_market_data_incremental_refresh,
        }

        self.register_handlers(handlers)

    def register_handlers(self, handlers):
        for msg_type, handler in handlers.items():
            self._handlers[msg_type] = handler

    async def get_security_list(self):
        sequence_number = self.session.store.increment_local_sequence_number()
        msg = message.Message.create_security_list_request(
            sequence_number=sequence_number,
            config=self.config
        )
        await self.session.send_message(msg)

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
        sequence_number = self.session.store.increment_local_sequence_number()
        msg = message.Message.create_market_data_request_message(
            sequence_number, self.config, symbols, entry_types
        )
        request_id = msg.get(fixation.constants.FixTag.MDReqID)

        self.session.store.register_symbol_request_mapping(symbols, request_id)
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
            entry_type = msg.get(fixation.constants.FixTag.MDEntryType)
            price = msg.get(fixation.constants.FixTag.MDEntryPx)
            size = msg.get(fixation.constants.FixTag.MDEntrySize)

            if entry_type in [
                constants.MDEntryType.OFFER,
                constants.MDEntryType.BID
            ]:
                book[fixation.constants.FixTag.MDEntryType] = {
                    'price': price,
                    'size': size
                }

            if entry_type == constants.MDEntryType.TRADE:
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
                await self.session.login()
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

        sequence_number = self.session.store.increment_local_sequence_number()
        msg = message.Message.create_new_order_message(
            sequence_number=sequence_number,
            config=self.config,
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
        sequence_number = msg.get(fixation.constants.FixTag.RefSeqNum)
        reject_explanation = msg.get(fixation.constants.FixTag.Text)
        ref_msg_type = msg.get(fixation.constants.FixTag.RefMsgType)
        business_reject_reason = msg.get(
            fixation.constants.FixTag.BusinessRejectReason)

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
