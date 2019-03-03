from datetime import datetime
import time
import uuid

import aioredis

from fixtrate.message import FixMessage
from .base import FixStoreInterface, FixStore
from fixtrate.utils.iterators import chunked


class RedisStore(FixStore):

    def __init__(self, redis, prefix='fix'):
        self.redis = redis
        self.prefix = prefix

    def make_redis_key(self, session_id, key):
        return ':'.join(filter(None, (
            self.prefix, session_id, key)))

    async def get_local(self, session):
        seq_num = await self.redis.get(
            self.make_redis_key(session.id, 'seq_num_local'))
        seq_num = seq_num or await self.incr_local(session)
        return int(seq_num)

    async def get_remote(self, session):
        seq_num = await self.redis.get(
            self.make_redis_key(session.id, 'seq_num_remote'))
        seq_num = seq_num or await self.incr_remote(session)
        return int(seq_num)

    async def incr_local(self, session):
        seq_num = await self.redis.incr(
            self.make_redis_key(session.id, 'seq_num_local'))
        return int(seq_num)

    async def incr_remote(self, session):
        seq_num = await self.redis.incr(
            self.make_redis_key(session.id, 'seq_num_remote'))
        return int(seq_num)

    async def set_local(self, session, new_seq_num):
        await self.redis.set(
            self.make_redis_key(session.id, 'seq_num_local'),
            str(new_seq_num))

    async def set_remote(self, session, new_seq_num):
        await self.redis.set(
            self.make_redis_key(session.id, 'seq_num_remote'),
            str(new_seq_num))

    async def store_message(self, session, msg):
        uid = str(uuid.uuid4())
        store_time = time.time()
        await self.redis.zadd(
            self.make_redis_key(session.id, 'messages_by_time'),
            store_time,
            uid
        )
        await self.redis.hset(
            self.make_redis_key(session.id, 'messages'),
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
        if isinstance(start, datetime):
            start = start.timestamp()
        if isinstance(end, datetime):
            end = end.timestamp()

        kwargs = {}
        if start is not None:
            kwargs['min'] = start
        if end is not None:
            kwargs['max'] = end

        uids = await self.redis.zrangebyscore(
            self.make_redis_key(session.id, 'messages_by_time'), **kwargs)

        for chunk in chunked(uids, 500):
            msgs = await self.redis.hmget(
                self.make_redis_key(session.id, 'messages'), *chunk)
            for msg in msgs:
                msg = FixMessage.from_raw(msg)
                if not min <= msg.seq_num <= max:
                    continue

                if direction is not None:
                    sender = msg.get(49)
                    is_sent = sender == session.config['sender_comp_id']

                    if direction == 'sent' and not is_sent:
                        continue
                    if direction == 'received' and is_sent:
                        continue

                yield msg


class RedisStoreInterface(FixStoreInterface):

    def __init__(self, redis_url, prefix='fix'):
        self.redis_url = redis_url
        self.prefix = prefix
        self.redis = None

    async def connect(self, engine):
        if self.redis is None:
            self.redis = await aioredis.create_redis_pool(
                self.redis_url, minsize=5, maxsize=10)
        return RedisStore(self.redis, self.prefix)

    async def close(self, engine):
        self.redis.close()
        await self.redis.wait_closed()
