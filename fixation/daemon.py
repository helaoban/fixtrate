import asyncio

from fixation import (
    config, session,
    store, rpc
)


class FixDaemon(object):

    def __init__(self, conf=None):
        self.session = None
        self.rpc_server = None
        self.loop = asyncio.get_event_loop()

        if conf is None:
            conf = config.get_config_from_env()
        else:
            config.validate_config(conf)

        self.config = conf

    async def main(self):
        self.session = session.FixSession(
            conf=self.config,
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
