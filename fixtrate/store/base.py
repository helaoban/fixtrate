import abc


class FixStore(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    async def incr_local(self, session):
        pass

    @abc.abstractmethod
    async def incr_remote(self, session):
        pass

    @abc.abstractmethod
    async def get_local(self, session):
        pass

    @abc.abstractmethod
    async def get_remote(self, session):
        pass

    @abc.abstractmethod
    async def set_local(self, session, new_seq_num):
        pass

    @abc.abstractmethod
    async def set_remote(self, session, new_seq_num):
        pass

    @abc.abstractmethod
    async def store_message(self, session, msg):
        pass

    @abc.abstractmethod
    async def get_messages(
        self,
        session,
        start=None,
        end=None,
        min=float('-inf'),
        max=float('inf'),
        direction=None
    ):
        pass
