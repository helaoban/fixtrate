from datetime import datetime
import time
import uuid

from fixtrate.message import FixMessage
from fixtrate.store import FixStore
from fixtrate.utils import chunked


class FixRedisStore(FixStore):

    def __init__(self, redis, session_id):
        self._redis = redis
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
