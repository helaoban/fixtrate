import asyncio
import collections

import aioredis

from fixation import (
    config, session,
    rpc, constants as fc,
    utils, store as fs,
    signals
)
from fixation.factories import fix42


class FixClient(object):

    def __init__(self, conf=None):
        conf = conf or config.get_config_from_env()
        config.validate_config(conf)
        self._config = conf
        self._session = None
        self._rpc_server = None
        self._loop = asyncio.get_event_loop()
        self._tags = getattr(fc.FixTag, self._config['FIX_VERSION'].name)

    async def send_test_request(self):
        msg = fix42.test_request()
        await self._session.send_message(msg)

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
        account = self._config['FIX_ACCOUNT']
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
        await self._session.send_message(msg)

    async def cancel_replace_order(
            self,
            order_id,
            symbol,
            quantity,
            side,
            order_type,
            price=None,
    ):
        account = self._config['FIX_ACCOUNT']
        msg = fix42.cancel_replace(
            account=account,
            orig_cl_order_id=order_id,
            symbol=symbol,
            side=fc.Side[side],
            order_type=fc.OrdType[order_type],
            quantity=quantity,
            price=price
        )
        await self._session.send_message(msg)

    async def cancel_order(
        self,
        order_id,
        symbol,
        side,
        quantity
    ):
        account = self._config['FIX_ACCOUNT']
        msg = fix42.cancel(
            account=account,
            orig_cl_order_id=order_id,
            symbol=symbol,
            side=fc.Side[side],
            quantity=quantity
        )
        await self._session.send_message(msg)

    async def order_status(
        self,
        order_id='*'
    ):
        msg = fix42.order_status(
            cl_order_id=order_id,
        )
        account = self._config['FIX_ACCOUNT']
        msg.append_pair(self._tags.Account, account)
        await self._session.send_message(msg)

    async def get_security_list(self):
        msg = fix42.security_list()
        await self._session.send_message(msg)

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
        await self._session.send_message(msg)

    def handle_market_data_full_refresh(self, msg):
        market_request_id = msg.get(262)
        if market_request_id is None:
            return
        symbol = msg.get(55)
        number_of_entries = msg.get(268)

        book = collections.defaultdict(list)
        trades = []
        for i in range(number_of_entries):
            entry_type = msg.get(self._tags.MDEntryType)
            price = msg.get(self._tags.MDEntryPx)
            size = msg.get(self._tags.MDEntrySize)

            if entry_type in [
                fc.MDEntryType.OFFER,
                fc.MDEntryType.BID
            ]:
                book[self._tags.MDEntryType] = {
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

    def handle_order_cancel_reject(self, msg):
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
        msg_type = fc.FixMsgType(msg.get(self._tags.MsgType))
        handler = self.dispatch_message(msg_type)
        if handler:
            if utils.is_coro(handler):
                await handler(msg)
            else:
                handler(msg)

    async def main(self):

        redis_pool = await aioredis.create_redis_pool(
            'redis://localhost', minsize=5, maxsize=10)

        store = fs.FixRedisStore(redis_pool, self._config)

        self._session = session.FixSession(
            conf=self._config,
            store=store,
            loop=self._loop,
        )
        self._rpc_server = rpc.RPCServer(
            self,
            loop=self._loop
        )

        @signals.message_received.connect
        def print_incoming_to_console(sender, msg):
            print('{} ({}) <--'.format(msg.msg_type.name, msg.seq_num))

        @signals.message_sent.connect
        def print_outgoing_to_console(sender, msg):
            print('{} ({}) -->'.format(msg.msg_type.name, msg.seq_num))

        @signals.sequence_gap.connect
        def debug_sequence_gap(sender, exc):
            print(exc)

        while True:
            try:
                async with self._session.connect():
                    await self._session.logon()
                    await self._rpc_server.start()

                    async for msg in self._session:
                        await self.handle_message(msg)

                    await self._session.logoff()

            except ConnectionError:
                continue
            except asyncio.CancelledError:
                break

        await self._rpc_server.stop()

    def __call__(self):
        task = self._loop.create_task(self.main())
        try:
            self._loop.run_until_complete(task)
        except (SystemExit, KeyboardInterrupt):
            task.cancel()
            self._loop.run_until_complete(task)
