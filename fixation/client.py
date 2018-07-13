import asyncio
import collections

from fixation import (
    config, session,
    rpc, constants as fc
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

    async def place_order(self, data):
        msg = fix42.new_order(
            account='qafa001',
            symbol=data['params']['symbol'],
            quantity=data['params']['quantity'],
            side=data['params']['side'],
            order_type=fc.OrdType[['params']['order_type']],
            price=data['params'].get('price'),
            currency='USD',
            ex_destination='SMART'
        )
        await self.session.send_message(msg)

    async def cancel_replace_order(self, data):
        msg = fix42.cancel_replace(
            account='qafa001',
            orig_cl_order_id=data['params']['orig_cl_order_id'],
            symbol=data['params']['symbol'],
            side=data['params']['side'],
            quantity=data['params']['quantity'],
            order_type=data['params']['order_type'],
            price=data['params'].get('price')

        )
        await self.session.send_message(msg)

    async def cancel_order(self, data):
        msg = fix42.cancel(
            account='qafa001',
            orig_cl_order_id=data['params']['orig_cl_order_id'],
            symbol=data['params']['symbol'],
            side=data['params']['side'],
        )
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

    async def send_test_request(self):
        msg = fix42.test_request()
        await self.session.send_message(msg)

    async def main(self):
        self.session = session.FixSession(
            conf=self.config,
            loop=self.loop,
        )
        self.rpc_server = rpc.RPCServer(
            self,
            loop=self.loop
        )

        conn = await self.session.connect()
        await self.session.logon()
        await self.rpc_server.start()

        try:
            async for msg in self.session:
                pass
        except asyncio.CancelledError:
            print('Closing...')
            await conn.close()

    def __call__(self):
        task = self.loop.create_task(self.main())
        try:
            self.loop.run_until_complete(task)
        except (SystemExit, KeyboardInterrupt):
            task.cancel()
            self.loop.run_until_complete(task)
