class Transport:

    async def read(self):
        raise NotImplementedError

    async def write(self, msg):
        raise NotImplementedError

    async def connect(self, url):
        raise NotImplementedError

    async def close(self):
        raise NotImplementedError

    async def is_closing(self):
        raise NotImplementedError
