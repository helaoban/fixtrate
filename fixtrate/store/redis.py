from datetime import datetime
import time
import uuid

import aioredis

from fixtrate.message import FixMessage
from .base import FixStoreInterface, FixStore
from fixtrate.utils.iterators import chunked


class RedisStore(FixStore):

    def __init__(self, redis, prefix=None):
        self.redis = redis
        self.prefix = prefix

    def make_redis_key(self, session_id, key):
        return ':'.join(filter(None, (
            self.prefix, str(session_id), key)))

    async def get_local(self, session_id):
        seq_num = await self.redis.get(
            self.make_redis_key(session_id, 'seq_num_local'))
        seq_num = seq_num or await self.incr_local(session_id)
        return int(seq_num)

    async def get_remote(self, session_id):
        seq_num = await self.redis.get(
            self.make_redis_key(session_id, 'seq_num_remote'))
        seq_num = seq_num or await self.incr_remote(session_id)
        return int(seq_num)

    async def incr_local(self, session_id):
        seq_num = await self.redis.incr(
            self.make_redis_key(session_id, 'seq_num_local'))
        return int(seq_num)

    async def incr_remote(self, session_id):
        seq_num = await self.redis.incr(
            self.make_redis_key(session_id, 'seq_num_remote'))
        return int(seq_num)

    async def set_local(self, session_id, new_seq_num):
        await self.redis.set(
            self.make_redis_key(session_id, 'seq_num_local'),
            str(new_seq_num))

    async def set_remote(self, session_id, new_seq_num):
        await self.redis.set(
            self.make_redis_key(session_id, 'seq_num_remote'),
            str(new_seq_num))

    async def store_message(self, session_id, msg):
        uid = str(uuid.uuid4())
        store_time = time.time()

        await self.redis.hset(
            self.make_redis_key(session_id, 'messages'),
            uid,
            msg.encode()
        )

        await self.redis.zadd(
            self.make_redis_key(session_id, 'messages_by_time'),
            store_time,
            uid
        )

        sent_or_received = 'messages_%s' % (
            'sent' if msg.get(49) == session_id.sender
            else 'received'
        )

        await self.redis.zadd(
            self.make_redis_key(session_id, sent_or_received),
            msg.seq_num,
            uid
        )
        return uid

    async def get_sent(
        self,
        session_id,
        min=float('-inf'),
        max=float('inf'),
        limit=None
    ):
        if limit is None:
            limit = -1
        if limit > 0:
            limit = limit + 1
        message_ids = await self.redis.zrevrangebyscore(
            self.make_redis_key(session_id, 'messages_sent'),
            min=min, max=max, offset=0, count=limit
        )
        if len(message_ids) == 0:
            return []
        message_ids = list(reversed(message_ids))
        key = self.make_redis_key(session_id, 'messages')
        msgs = await self.redis.hmget(key, *message_ids)
        return [FixMessage.from_raw(m) for m in msgs]

    async def get_received(
        self,
        session_id,
        min=float('-inf'),
        max=float('inf'),
        limit=None
    ):
        if limit is None:
            limit = -1
        if limit > 0:
            limit = limit + 1
        message_ids = await self.redis.zrevrangebyscore(
            self.make_redis_key(session_id, 'messages_received'),
            min=min, max=max, offset=0, count=limit
        )
        if len(message_ids) == 0:
            return []
        message_ids = list(reversed(message_ids))
        key = self.make_redis_key(session_id, 'messages')
        msgs = await self.redis.hmget(key, *message_ids)
        return [FixMessage.from_raw(m) for m in msgs]

    async def get_messages(
        self,
        session_id,
        start=float('-inf'),
        end=float('inf'),
        limit=None,
    ):
        if limit is None:
            limit = -1
        if limit > 0:
            limit = limit + 1
        message_ids = await self.redis.zrevrangebyscore(
            self.make_redis_key(session_id, 'messages_by_time'),
            min=start, max=end, offset=0, count=limit
        )
        if len(message_ids) == 0:
            return []
        message_ids = list(reversed(message_ids))

        key = self.make_redis_key(session_id, 'messages')
        msgs = await self.redis.hmget(key, *message_ids)
        msgs = [FixMessage.from_raw(m) for m in msgs]
        return msgs

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
