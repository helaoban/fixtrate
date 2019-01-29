from copy import deepcopy
import time
import uuid
from collections import OrderedDict

from sortedcontainers import SortedDict
from fixtrate.message import FixMessage
from fixtrate.store import FixStore


class FixMemoryStore(FixStore):

    def __init__(self, session_id):
        self._local_seq_num = 1
        self._remote_seq_num = 1
        self._messages = OrderedDict()
        self._local = SortedDict()
        self._remote = SortedDict()
        self._config = None
        self._session_id = session_id

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
        uid = uuid.uuid4()
        self._messages[uid] = msg.encode()
        return uid

    async def get_messages(
        self,
        start=None,
        end=None,
        min=float('-inf'),
        max=float('inf'),
        direction=None
    ):
        msgs = deepcopy(self._messages)
        for msg in msgs.values():
            msg = FixMessage.from_raw(msg)
            if not min <= msg.seq_num <= max:
                continue
            if direction is not None:
                sender = msg.get(49)
                is_sent = sender == self._session_id.sender_comp_id

                if direction == 'sent' and not is_sent:
                    continue
                if direction == 'received' and is_sent:
                    continue

            yield msg

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
