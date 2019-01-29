import abc


class FixStore(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    async def incr_seq_num(self, remote=False):
        pass

    @abc.abstractmethod
    async def get_seq_num(self, remote=False):
        pass

    @abc.abstractmethod
    async def set_seq_num(self, seq_num, remote=False):
        pass

    @abc.abstractmethod
    async def store_message(self, msg):
        pass

    @abc.abstractmethod
    async def get_messages(self):
        pass

    @abc.abstractmethod
    async def new_session(self):
        pass
