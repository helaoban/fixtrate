import abc
import json
import time

from sortedcontainers import SortedDict

from .parse import FixParser


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
    async def store_message(self, msg, remote=False):
        pass

    @abc.abstractmethod
    async def get_message(self, uid):
        pass

    @abc.abstractmethod
    async def get_messages(self):
        pass

    @abc.abstractmethod
    async def get_messages_by_seq_num(self, start=None, end=None, remote=False):
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

    @staticmethod
    def decode_message(msg, uid=None):
        parser = FixParser()
        parser.append_buffer(msg)
        return parser.get_message(uid)

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
            uid: self.decode_message(msg, uid)
            for uid, msg in self._messages.items()
        }

    async def get_messages_by_seq_num(self, start=1, end='inf', remote=False):
        end = end or 'inf'
        uids_by_seq = self._local
        if remote:
            uids_by_seq = self._remote
        uids_by_seq = {
            int(seq_num): uid
            for seq_num, uid in uids_by_seq.items()
            if start <= int(seq_num) <= float(end)
        }
        msgs = await self.get_messages()
        return SortedDict({
            int(seq_num): msgs[uid]
            for seq_num, uid
            in uids_by_seq.items()
        })

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


class FixRedisStore(FixStore):

    def __init__(self, redis_pool, session_id):
        self._redis = redis_pool
        self._session_id = session_id

    def _make_namespaced_key(self, key):
        return str(self._session_id) + ':' + key

    @staticmethod
    def decode_message(msg, uid=None):
        parser = FixParser()
        parser.append_buffer(msg)
        return parser.get_message(uid)

    async def incr_seq_num(self, remote=False):
        key = 'seq_num_{}'.format('remote' if remote else 'local')
        seq_num = await self._redis.incr(
            self._make_namespaced_key(key))
        return int(seq_num)

    async def set_seq_num(self, seq_num, remote=False):
        key = 'seq_num_{}'.format('remote' if remote else 'local')
        await self._redis.set(
            self._make_namespaced_key(key), str(seq_num))

    async def get_seq_num(self, remote=False):
        key = 'seq_num_{}'.format('remote' if remote else 'local')
        seq_num = await self._redis.get(
            self._make_namespaced_key(key))
        seq_num = seq_num or await self.incr_seq_num(remote=remote)
        return int(seq_num)

    async def store_message(self, msg, remote=False):
        direction = 'remote' if remote else 'local'
        seq_num = msg.get(34)
        await self._redis.hset(
            self._make_namespaced_key('messages'),
            msg.uid, msg.encode())
        await self._redis.zadd(
            self._make_namespaced_key(direction),
            int(seq_num), msg.uid)
        await self._redis.zadd(
            self._make_namespaced_key('messages_by_time'),
            time.time(), msg.uid)

    async def get_message(self, uid):
        msg = await self._redis.hget(
            self._make_namespaced_key('messages'), uid)
        if msg:
            return self.decode_message(msg, uid)

    async def get_messages(self):
        msgs = await self._redis.hgetall(
            self._make_namespaced_key('messages'))
        msgs = msgs or {}
        return {
            uid: self.decode_message(msg, uid.decode())
            for uid, msg in msgs.items()
        }

    async def get_messages_by_seq_num(
        self,
        start=1,
        end='inf',
        remote=False
    ):
        direction = 'remote' if remote else 'local'
        uids_by_seq_num = await self._redis.zrangebyscore(
            self._make_namespaced_key(direction),
            min=start, max=end, withscores=True)
        msgs = await self.get_messages()
        return SortedDict({
            int(seq_num): msgs[uid]
            for uid, seq_num
            in uids_by_seq_num
            if seq_num is not None
        })

    async def get_messages_by_time(self):
        uids_by_time = await self._redis.zrange(
            self._make_namespaced_key('messages_by_time'),
            start=0, stop=-1, withscores=True)
        msgs = await self.get_messages()
        return SortedDict({
            timestamp: msgs[uid]
            for uid, timestamp
            in uids_by_time
        })

    async def store_config(self, conf):
        jsoned = json.dumps(conf)
        await self._redis.set(self._make_namespaced_key('config'), jsoned)

    async def get_config(self):
        conf = await self._redis.get(self._make_namespaced_key('config'))
        return json.loads(conf.decode())

    async def new_session(self):
        for key in ['messages', 'remote', 'local', 'messages_by_time']:
            await self._redis.delete(key)
        await self.set_seq_num(1)
        await self.set_seq_num(1, remote=True)
