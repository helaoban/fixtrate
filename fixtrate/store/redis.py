from datetime import datetime
import time
import uuid

import aioredis

from fixtrate.message import FixMessage
from fixtrate.store import FixStore
from fixtrate.utils.iterators import chunked


class FixRedisStore(FixStore):

    def make_redis_key(self, session, key):
        parts = (
            'VERSION',
            'SENDER_COMP_ID',
            'TARGET_COMP_ID',
            'SESSION_QUALIFIER'
        )
        store_conf = session.config['store_options']
        prefix = store_conf.get('prefix', 'fix')
        sid = ':'.join(filter(
            None, (session.config.get(p) for p in parts)))
        return ':'.join(filter(None, (prefix, sid, key)))

    async def open(self, session):
        redis_url = session.config['store_options']['redis_url']
        self._redis = await aioredis.create_redis(redis_url)

    async def close(self, session):
        self._redis.close()
        await self._redis.wait_closed()

    async def get_local(self, session):
        seq_num = await self._redis.get(
            self.make_redis_key(session, 'seq_num_local'))
        seq_num = seq_num or await self.incr_local(session)
        return int(seq_num)

    async def get_remote(self, session):
        seq_num = await self._redis.get(
            self.make_redis_key(session, 'seq_num_remote'))
        seq_num = seq_num or await self.incr_remote(session)
        return int(seq_num)

    async def incr_local(self, session):
        seq_num = await self._redis.incr(
            self.make_redis_key(session, 'seq_num_local'))
        return int(seq_num)

    async def incr_remote(self, session):
        seq_num = await self._redis.incr(
            self.make_redis_key(session, 'seq_num_remote'))
        return int(seq_num)

    async def set_local(self, session, new_seq_num):
        await self._redis.set(
            self.make_redis_key(session, 'seq_num_local'),
            str(new_seq_num))

    async def set_remote(self, session, new_seq_num):
        await self._redis.set(
            self.make_redis_key(session, 'seq_num_remote'),
            str(new_seq_num))

    async def store_message(self, session, msg):
        uid = str(uuid.uuid4())
        store_time = time.time()
        await self._redis.zadd(
            self.make_redis_key(session, 'messages_by_time'),
            store_time,
            uid
        )
        await self._redis.hset(
            self.make_redis_key(session, 'messages'),
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

        uids = await self._redis.zrangebyscore(
            self.make_redis_key(session, 'messages_by_time'), **kwargs)

        for chunk in chunked(uids, 500):
            msgs = await self._redis.hmget(
                self.make_redis_key(session, 'messages'), *chunk)
            for msg in msgs:
                msg = FixMessage.from_raw(msg)
                if not min <= msg.seq_num <= max:
                    continue

                if direction is not None:
                    sender = msg.get(49)
                    is_sent = sender == session.config['SENDER_COMP_ID']

                    if direction == 'sent' and not is_sent:
                        continue
                    if direction == 'received' and is_sent:
                        continue

                yield msg
