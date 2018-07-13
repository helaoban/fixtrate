import asyncio
import collections

from fixation import (
    config, session,
    rpc, constants as fc,
    utils
)
from fixation.factories import fix42


class FixClient(object):

    def __init__(self, conf=None):
        self.session = None
        self.rpc_server = None
        self.loop = asyncio.get_event_loop()

        if conf is None:
            conf = config.get_config_from_env()
        else:
            config.validate_config(conf)

        self.config = conf

        self.TAGS = fc.FixTag.FIX42

    async def place_order(
            self,
            symbol,
            quantity,
            side,
            order_type,
            price=None,
            currency='USD',
            ex_destination='SMART',
            time_in_force=None
    ):
        account = self.config['FIX_ACCOUNT']
        if time_in_force is not None:
            time_in_force = fc.TimeInForce[time_in_force]
        msg = fix42.new_order(
            account=account,
            symbol=symbol,
            quantity=quantity,
            side=fc.Side[side],
            order_type=fc.OrdType[order_type],
            price=price,
            currency=currency,
            ex_destination=ex_destination,
            time_in_force=time_in_force
        )
        await self.session.send_message(msg)

    async def cancel_replace_order(
            self,
            order_id,
            symbol,
            quantity,
            side,
            order_type,
            price=None,
    ):
        account = self.config['FIX_ACCOUNT']
        msg = fix42.cancel_replace(
            account=account,
            orig_cl_order_id=order_id,
            symbol=symbol,
            side=fc.Side[side],
            order_type=fc.OrdType[order_type],
            quantity=quantity,
            price=price
        )
        await self.session.send_message(msg)

    async def cancel_order(
        self,
        order_id,
        symbol,
        side,
        quantity
    ):
        account = self.config['FIX_ACCOUNT']
        msg = fix42.cancel(
            account=account,
            orig_cl_order_id=order_id,
            symbol=symbol,
            side=fc.Side[side],
            quantity=quantity
        )
        await self.session.send_message(msg)

    async def order_status(
        self,
        order_id='*'
    ):
        msg = fix42.order_status(
            cl_order_id=order_id,
        )
        account = self.config['FIX_ACCOUNT']
        msg.append_pair(self.TAGS.Account, account)
        await self.session.send_message(msg)

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

    def handle_market_data_reject(self, msg):
        pass

    def handle_execution_report(self, msg):
        pass

    def handle_order_cancel_reject(self):
        pass

    def dispatch_message(self, msg_type):
        handler = {
            fc.FixMsgType.MarketDataIncrementalRefresh: self.handle_market_data_incremental_refresh,
            fc.FixMsgType.MarketDataSnapshotFullRefresh: self.handle_market_data_full_refresh,
            fc.FixMsgType.MarketDataRequestReject: self.handle_market_data_reject,
            fc.FixMsgType.ExecutionReport: self.handle_execution_report,
            fc.FixMsgType.OrderCancelReject: self.handle_order_cancel_reject,
        }.get(msg_type)
        return handler

    async def handle_message(self, msg):
        msg_type = fc.FixMsgType(msg.get(self.TAGS.MsgType))
        handler = self.dispatch_message(msg_type)
        if handler:
            if utils.is_coro(handler):
                await handler(msg)
            else:
                handler(msg)

    async def main(self):
        self.session = session.FixSession(
            conf=self.config,
            loop=self.loop,
        )
        self.rpc_server = rpc.RPCServer(
            self,
            loop=self.loop
        )

        while True:
            try:
                async with self.session.connect():
                    await self.session.logon()
                    await self.rpc_server.start()

                    async for msg in self.session:
                        await self.handle_message(msg)

            except ConnectionError:
                continue
            except asyncio.CancelledError:
                break

        await self.rpc_server.stop()

    def __call__(self):
        task = self.loop.create_task(self.main())
        try:
            self.loop.run_until_complete(task)
        except (SystemExit, KeyboardInterrupt):
            task.cancel()
            self.loop.run_until_complete(task)
