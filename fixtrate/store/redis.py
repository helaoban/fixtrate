from datetime import datetime
import time
import uuid

from fixtrate.message import FixMessage
from fixtrate.store import FixStore
from fixtrate.utils import chunked


class FixRedisStore(FixStore):

    def __init__(self, redis, prefix='fix:'):
        self._redis = redis
        self._prefix = prefix

    def make_redis_key(self, session, key):
        sid = session.config.get_sid()
        return ':'.join(filter(None, (self._prefix, sid, key)))

    async def get_local(self, session):
        sid = session.config.get_sid()
        seq_num = await self._redis.get(
            self.make_redis_key(sid, 'seq_num_local'))
        seq_num = seq_num or await self.incr_local()
        return int(seq_num)

    async def get_remote(self, session):
        sid = session.config.get_sid()
        seq_num = await self._redis.get(
            self.make_redis_key(sid, 'seq_num_remote'))
        seq_num = seq_num or await self.incr_remote()
        return int(seq_num)

    async def incr_local(self, session):
        sid = session.config.get_sid()
        seq_num = await self._redis.incr(
            self.make_redis_key(sid, 'seq_num_local'))
        return int(seq_num)

    async def incr_remote(self, session):
        sid = session.config.get_sid()
        seq_num = await self._redis.incr(
            self.make_redis_key(sid, 'seq_num_remote'))
        return int(seq_num)

    async def set_local(self, session, new_seq_num):
        sid = session.config.get_sid()
        await self._redis.set(
            self.make_redis_key(sid, 'seq_num_local'),
            str(new_seq_num))

    async def set_remote(self, session, new_seq_num):
        sid = session.config.get_sid()
        await self._redis.set(
            self.make_redis_key(sid, 'seq_num_remote'),
            str(new_seq_num))

    async def store_message(self, session, msg):
        sid = session.config.get_sid()
        uid = uuid.uuid4()
        store_time = time.time()
        await self._redis.zadd(
            self.make_redis_key(sid, 'messages_by_time'),
            store_time,
            uid
        )
        await self._redis.hset(
            self.make_redis_key(sid, 'messages'),
            uid,
            msg.encode()
        )
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
            self.make_redis_key(sid, 'messages_by_time'), **kwargs)

        for chunk in chunked(uids, 500):
            msgs = await self._redis.hmget(
                self.make_redis_key(sid, 'messages'), *chunk)
            for msg in msgs:
                msg = FixMessage.from_raw(msg)
                if not min <= msg.seq_num() <= max:
                    continue

                if direction is not None:
                    sender = msg.get(49)
                    is_sent = sender == sid.sender_comp_id

                    if direction == 'sent' and not is_sent:
                        continue
                    if direction == 'received' and is_sent:
                        continue

                yield msg
