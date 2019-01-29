import abc
from datetime import datetime
import json
import time
import uuid

from sortedcontainers import SortedDict
from .message import FixMessage
from fixtrate.utils import chunked


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
    async def get_message(self, uid):
        pass

    @abc.abstractmethod
    async def get_messages(self):
        pass

    @abc.abstractmethod
    async def new_session(self):
        pass

    @abc.abstractmethod
    async def store_config(self, conf):
        pass

    @abc.abstractmethod
    async def get_config(self):
        pass


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


class FixRedisStore(FixStore):

    def __init__(self, redis_pool, session_id):
        self._redis = redis_pool
        self._session_id = session_id

    def make_key(self, key):
        return '{session_id!s}:{key}'.format(
            session_id=self._session_id,
            key=key
        )

    async def incr_seq_num(self, remote=False):
        key = 'seq_num_{}'.format('remote' if remote else 'local')
        seq_num = await self._redis.incr(
            self.make_key(key))
        return int(seq_num)

    async def set_seq_num(self, seq_num, remote=False):
        key = 'seq_num_{}'.format('remote' if remote else 'local')
        await self._redis.set(
            self.make_key(key), str(seq_num))

    async def get_seq_num(self, remote=False):
        key = 'seq_num_{}'.format('remote' if remote else 'local')
        seq_num = await self._redis.get(
            self.make_key(key))
        seq_num = seq_num or await self.incr_seq_num(remote=remote)
        return int(seq_num)

    async def store_message(self, msg):
        uid = uuid.uuid4()
        store_time = time.time()
        await self._redis.zadd(
            self.make_key('messages_by_time'), store_time, uid)
        await self._redis.hset(
            self.make_key('messages'), uid, msg.encode())
        return uid

    async def get_message(self, uid):
        msg = await self._redis.hget(
            self.make_key('messages'), uid)
        if msg:
            return FixMessage.from_raw(msg)

    async def get_messages(
        self,
        start=None,
        end=None,
        min=float('-inf'),
        max=float('inf'),
        direction=None
    ):

        if isinstance(start, datetime):
            start = start.timestamp()
        if isinstance(end, datetime):
            end = end.timestamp()

        kwargs = {}
        if start is not None:
            kwargs['min'] = start
        if end is not None:
            kwargs['max'] = end

        uids = await self._redis.zrangebyscore(
            self.make_key('messages_by_time'), **kwargs)

        for chunk in chunked(uids, 500):
            msgs = await self._redis.hmget(self.make_key('messages'), *chunk)
            for msg in msgs:
                msg = FixMessage.from_raw(msg)
                if not min <= msg.seq_num() <= max:
                    continue

                if direction is not None:
                    sender = msg.get(49)
                    is_sent = sender == self._session_id.sender_comp_id

                    if direction == 'sent' and not is_sent:
                        continue
                    if direction == 'received' and is_sent:
                        continue

                yield msg

    async def store_config(self, conf):
        jsoned = json.dumps(conf)
        await self._redis.set(self.make_key('config'), jsoned)

    async def get_config(self):
        conf = await self._redis.get(self.make_key('config'))
        return json.loads(conf.decode())

    async def new_session(self):
        for key in ['messages', 'remote', 'local', 'messages_by_time']:
            await self._redis.delete(key)
        await self.set_seq_num(1)
        await self.set_seq_num(1, remote=True)
