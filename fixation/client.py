import asyncio

from fixation import session, config, version, store


class FixClient(object):

    def __init__(self):
        self.session = None

        self.config = config.FixConfig(
            host='127.0.0.1',
            port=4000,
            sender_comp_id='qafa001',
            target_comp_id='IB',
            version=version.FixVersion.FIX42,
            heartbeat_interval=30,

        )

        self.loop = asyncio.get_event_loop()

    async def listen(self):
        self.session = session.FixSession(
            config=self.config, loop=self.loop,
            store=store.FixMemoryStore()
        )
        async with self.session.connect() as conn:
            await self.session.login()
            async for msg in self.session:
                print(msg)

    def __call__(self):
        try:
            self.loop.run_until_complete(self.listen())
        except (SystemExit, KeyboardInterrupt):
            pass
