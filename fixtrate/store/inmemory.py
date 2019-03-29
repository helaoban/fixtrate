from copy import deepcopy
import uuid
from collections import OrderedDict, defaultdict
import time

from fixtrate.message import FixMessage
from .base import FixStoreInterface, FixStore


class MemoryStore(FixStore):

    def __init__(self, data_store=None):
        if data_store is None:
            data_store = {}
        self._data = data_store

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
        uid = str(uuid.uuid4())
        store_time = time.time()
        msgs = self._get_messages(session_id)
        msgs[uid] = store_time, msg.encode()
        return uid

    async def get_sent(
        self,
        session_id,
        min=float('-inf'),
        max=float('inf'),
        limit=None
    ):
        msgs = self._get_messages(session_id)
        rv = []
        for time, msg in msgs.values():
            msg = FixMessage.from_raw(msg)
            if msg.get(49) != session_id.sender:
                continue
            if not min <= msg.seq_num <= max:
                continue
            rv.append(msg)
        if limit is not None:
            rv = rv[limit * -1:]
        return rv

    async def get_received(
        self,
        session_id,
        min=float('-inf'),
        max=float('inf'),
        limit=None
    ):
        msgs = self._get_messages(session_id)
        rv = []
        for time, msg in msgs.values():
            msg = FixMessage.from_raw(msg)
            if msg.get(49) != session_id.target:
                continue
            if not min <= msg.seq_num <= max:
                continue
            rv.append(msg)
        if limit is not None:
            rv = rv[limit * -1:]
        return rv

    def _get_messages(self, session_id):
        key = self.make_key(session_id, 'messages')
        return self._data.setdefault(key, OrderedDict())

    async def get_messages(
        self,
        session_id,
        start=float('-inf'),
        end=float('inf'),
        limit=None,
    ):
        rv = []
        msgs = self._get_messages(session_id)
        for time_, msg in msgs.values():
            if not start <= time_ <= end:
                continue
            rv.append(msg)
        if limit is not None:
            rv = rv[limit * -1:]
        return rv

    async def reset(self, session_id):
        self._data = {}
        await self.set_local(session_id, 1)
        await self.set_remote(session_id, 1)


class MemoryStoreInterface(FixStoreInterface):

    def __init__(self, data_store=None):
        if data_store is None:
            data_store = {}
        self.data_store = data_store

    async def connect(self, engine):
        return MemoryStore(self.data_store)

    async def close(self, engine):
        pass
