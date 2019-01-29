from sortedcontainers import SortedDict
from fixtrate.message import FixMessage
from fixtrate.store import FixStore


class FixMemoryStore(FixStore):

    def __init__(self):
        self._local_seq_num = 1
        self._remote_seq_num = 1
        self._messages = {}
        self._local = SortedDict()
        self._remote = SortedDict()
        self._config = None

    async def incr_seq_num(self, remote=False):
        if remote:
            self._remote_seq_num += 1
            return self._remote_seq_num
        else:
            self._local_seq_num += 1
            return self._local_seq_num

    async def get_seq_num(self, remote=False):
        if remote:
            return self._remote_seq_num or self.incr_seq_num(remote=True)
        else:
            return self._local_seq_num or self.incr_seq_num()

    async def set_seq_num(self, seq_num, remote=False):
        if remote:
            self._remote_seq_num = seq_num
        else:
            self._local_seq_num = seq_num

    async def store_message(self, msg, remote=False):
        seq_num = msg.get(34)
        self._messages[msg.uid] = msg.encode()
        if remote:
            self._remote[seq_num] = msg.uid
        else:
            self._local[seq_num] = msg.uid

    async def get_message(self, uid):
        return self._messages.get(uid)

    async def get_messages(self):
        return {
            uid: FixMessage.from_raw(msg)
            for uid, msg in self._messages.items()
        }

    async def new_session(self):
        self._messages = {}
        self._local = SortedDict()
        self._remote = SortedDict()
        self.set_seq_num(1)
        self.set_seq_num(1, remote=True)

    async def store_config(self, conf):
        self._config = conf

    async def get_config(self):
        return self._config

    async def __aiter__(self):
        messages = await self.get_messages()
        self.__messages = iter(messages.items())
        return self

    async def __anext__(self):
        try:
            return next(self.__messages)
        except StopIteration:
            self.__messages = None
            raise StopAsyncIteration
