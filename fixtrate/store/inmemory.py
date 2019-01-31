from copy import deepcopy
import uuid
from collections import OrderedDict

from fixtrate.message import FixMessage
from fixtrate.store import FixStore


class FixMemoryStore(FixStore):

    def __init__(self):
        self._local_seq_num = 1
        self._remote_seq_num = 1
        self._messages = OrderedDict()

    async def incr_local(self, session):
        self._local_seq_num += 1
        return self._local_seq_num

    async def incr_remote(self, session):
        self._remote_seq_num += 1
        return self._remote_seq_num

    async def get_local(self, session):
        return self._local_seq_num or self.incr_local()

    async def get_remote(self, session):
        return self._remote_seq_num or self.incr_remote()

    async def set_local(self, session, new_seq_num):
        self._local_seq_num = new_seq_num

    async def set_remote(self, session, new_seq_num):
        self._remote_seq_num = new_seq_num

    async def store_message(self, session, msg):
        uid = uuid.uuid4()
        self._messages[uid] = msg.encode()
        return uid

    async def get_messages(
        self,
        session,
        start=None,
        end=None,
        min=float('-inf'),
        max=float('inf'),
        direction=None
    ):
        sid = session.config.get_sid()
        msgs = deepcopy(self._messages)
        for msg in msgs.values():
            msg = FixMessage.from_raw(msg)
            if not min <= msg.seq_num <= max:
                continue
            if direction is not None:
                sender = msg.get(49)
                is_sent = sender == sid.sender_comp_id

                if direction == 'sent' and not is_sent:
                    continue
                if direction == 'received' and is_sent:
                    continue

            yield msg

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
