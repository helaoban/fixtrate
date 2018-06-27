import asyncio

from fixation import (
    config, constants,
    session, version,
    store, rpc, tags
)


class FixDaemon(object):

    def __init__(self):
        self.session = None
        self.rpc_server = None
        self.loop = asyncio.get_event_loop()

        self.config = config.FixConfig(
            host='127.0.0.1',
            port=4000,
            sender_comp_id='qafa001',
            target_comp_id='IB',
            version=version.FixVersion.FIX42,
            heartbeat_interval=30,

        )

    async def main(self):
        self.session = session.FixSession(
            config=self.config,
            loop=self.loop,
            store=store.FixMemoryStore()
        )
        self.rpc_server = rpc.RPCServer(
            self.session,
            loop=self.loop
        )

        conn = await self.session.connect()
        await self.session.login()
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
