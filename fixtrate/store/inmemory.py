from copy import deepcopy
import uuid
from collections import OrderedDict, defaultdict

from fixtrate.message import FixMessage
from .base import FixStoreInterface, FixStore


class MemoryStore(FixStore):

    def __init__(self, data_store=None):
        if data_store is None:
            data_store = {}
        self._data = data_store
        self._messages = defaultdict(OrderedDict)

    def make_key(self, session_id, key):
        return ':'.join((str(session_id), key))

    async def incr_local(self, session_id):
        key = self.make_key(session_id, 'seq_num_local')
        self._data[key] = self._data.get(key, 0) + 1
        return self._data[key]

    async def incr_remote(self, session_id):
        key = self.make_key(session_id, 'seq_num_remote')
        self._data[key] = self._data.get(key, 0) + 1
        return self._data[key]

    async def get_local(self, session_id):
        key = self.make_key(session_id, 'seq_num_local')
        seq_num = self._data.get(key)
        if seq_num is None:
            seq_num = await self.incr_local(session_id)
        return seq_num

    async def get_remote(self, session_id):
        key = self.make_key(session_id, 'seq_num_remote')
        seq_num = self._data.get(key)
        if seq_num is None:
            seq_num = await self.incr_remote(session_id)
        return seq_num

    async def set_local(self, session_id, new_seq_num):
        key = self.make_key(session_id, 'seq_num_local')
        self._data[key] = new_seq_num

    async def set_remote(self, session_id, new_seq_num):
        key = self.make_key(session_id, 'seq_num_remote')
        self._data[key] = new_seq_num

    async def store_message(self, session_id, msg):
        key = self.make_key(session_id, 'messages')
        uid = str(uuid.uuid4())
        try:
            self._data[key][uid] = msg.encode()
        except KeyError:
            self._data[key] = OrderedDict(((uid, msg.encode()),))
        return uid

    async def get_messages(
        self,
        session_id,
        start=None,
        end=None,
        min=float('-inf'),
        max=float('inf'),
        direction=None
    ):
        key = self.make_key(session_id, 'messages')
        try:
            msgs = self._data[key]
        except KeyError:
            self._data[key] = msgs = OrderedDict()

        for msg in deepcopy(msgs).values():
            msg = FixMessage.from_raw(msg)
            if not min <= msg.seq_num <= max:
                continue
            if direction is not None:
                sender = msg.get(49)
                is_sent = sender == session_id.sender

                if direction == 'sent' and not is_sent:
                    continue
                if direction == 'received' and is_sent:
                    continue

            yield msg


class MemoryStoreInterface(FixStoreInterface):

    def __init__(self, data_store=None):
        if data_store is None:
            data_store = {}
        self.data_store = data_store

    async def connect(self, engine):
        return MemoryStore(self.data_store)

    async def close(self, engine):
        pass
