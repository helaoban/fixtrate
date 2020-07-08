import time
import uuid
import typing as t

import aioredis  # type: ignore

from fix.message import FixMessage
from .base import FixStore


if t.TYPE_CHECKING:
    from fix.config import FixSessionConfig


__all__ = ("RedisStore", )


remote_incr = """
    local v = redis.call("GET", KEYS[1])
    if v == nil then
        redis.call("SET", KEYS[1], "1")
    end
    local rv = redis.call("INCR", KEYS[1])
    return rv
"""

_get_msgs = """
    local function merge_tables(first, second)
        for k, v in pairs(second) do
            first[k] = v
        end
    end

    local function chunked(command, key, args)
        local results = {}
        local chunk_result = {}
        local args_len = #args
        local chunk_len = 1000
        for i = 1, args_len, chunk_len do
            chunk_result = redis.call(
                command,
                key,
                unpack(args, i, math.min(i + chunk_len -1, args_len))
            )
            merge_tables(results, chunk_result)
        end
        return results
    end

    local command
    if ARGV[1] == "ascending" then
        command = "ZRANGEBYSCORE"
    else
        command = "ZREVRANGEBYSCORE"
    end
    local msg_ids = redis.call(
            command, KEYS[1], ARGV[2], ARGV[3],
            "LIMIT", "0", ARGV[4]
    )
    if #msg_ids == 0 then
        return {}
    end
    return chunked("HMGET", KEYS[2], msg_ids)
"""


def _str_bound(val: float) -> str:
    if val == float("inf"):
        return "+inf"
    return str(val)


class RedisStore(FixStore):

    def __init__(
        self,
        config: "FixSessionConfig",
        redis: aioredis.Redis,
        prefix: t.Optional[str] = None
    ) -> None:
        self.redis: aioredis.Redis = redis
        self.prefix = prefix
        super().__init__(config)

    def _make_session_id(self) -> str:
        return ':'.join(filter(None, (
            self.config.version, self.config.sender,
            self.config.target, self.config.qualifier)))

    def _make_key(self, key: str) -> str:
        session_id = self._make_session_id()
        return ':'.join(filter(None, (
            self.prefix, session_id, key)))

    async def get_local(self) -> int:
        key = self._make_key('seq_num_local')
        seq_num = await self.redis.get(key)
        if seq_num is None:
            await self.redis.set(key, "0")
            return 0
        else:
            return int(seq_num)

    async def get_remote(self) -> int:
        key = self._make_key('seq_num_remote')
        seq_num = await self.redis.get(key)
        if seq_num is None:
            await self.redis.set(key, "1")
            return 1
        else:
            return int(seq_num)

    async def incr_local(self) -> int:
        seq_num = await self.redis.incr(
            self._make_key('seq_num_local'))
        return int(seq_num)

    async def incr_remote(self) -> int:
        key = self._make_key('seq_num_remote')
        seq_num = await self.redis.eval(remote_incr, keys=[key])
        return int(seq_num)

    async def set_local(self, new_seq_num: int) -> None:
        key = self._make_key('seq_num_local')
        await self.redis.set(key, str(new_seq_num))

    async def set_remote(self, new_seq_num: int) -> None:
        key = self._make_key('seq_num_remote')
        await self.redis.set(key, str(new_seq_num))

    async def store_msg(self, *msgs: FixMessage) -> None:
        for msg in msgs:
            uid = str(uuid.uuid4())

            key = self._make_key('messages')
            await self.redis.hset(key, uid, msg.encode())

            store_time = time.time()
            key = self._make_key('messages_by_time')
            await self.redis.zadd(key, store_time, uid)

            is_sent = msg.get_raw(49) == self.config.sender
            index = 'messages_%s' % ("sent" if is_sent else "received")
            key = self._make_key(index)
            await self.redis.zadd(key, msg.seq_num, uid)

    async def get_msgs(
        self,
        min: float = float("-inf"),
        max: float = float("inf"),
        limit: float = float("inf"),
        index: "str" = "by_time",
        sort: "str" = "ascending",
    ) -> t.AsyncIterator[FixMessage]:

        limit = -1 if limit == float("inf") else limit

        if sort == "descending":
            min, max = max, min

        id_key = self._make_key(f"messages_{index}")
        msg_key = self._make_key("messages")

        raw_msgs = await self.redis.eval(
            _get_msgs,
            keys=[id_key, msg_key],
            args=[sort, _str_bound(min), _str_bound(max), str(limit)],
        )

        for raw_msg in raw_msgs:
            msg = FixMessage.from_raw(raw_msg)
            if msg is None:
                raise TypeError(
                    f"Unable to parse fix message in store. "
                    f"The message may be corrupted. Raw msg: {raw_msg}")
            yield msg

    async def reset(self) -> None:
        for key in (
            'messages', 'messages_by_time',
            'messages_sent', 'messages_received'
        ):
            key = self._make_key(key)
            await self.redis.delete(key)

        # We have already exchanged
        await self.set_local(1)
        await self.set_remote(2)

    async def close(self) -> None:
        if self.redis is not None:
            self.redis.close()
            await self.redis.wait_closed()
