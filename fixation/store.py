import json
import time

import redis
from sortedcontainers import SortedDict

from fixation import parse as fp, config


class FixStore(object):

    def incr_seq_num(self, remote=False):
        raise NotImplementedError

    def get_seq_num(self, remote=False):
        raise NotImplementedError

    def set_seq_num(self, seq_num, remote=False):
        raise NotImplementedError

    def store_message(self, msg, remote=False):
        raise NotImplementedError

    def get_message(self, uid):
        raise NotImplementedError

    def get_messages(self, keys=None):
        raise NotImplementedError

    def get_messages_by_seq_num(self, remote=False):
        raise NotImplementedError

    def new_session(self):
        raise NotImplementedError

    def store_config(self, conf):
        raise NotImplementedError

    def get_config(self):
        raise NotImplementedError


class FixMemoryStore(FixStore):

    def __init__(self):
        self._local_seq_num = 0
        self._remote_seq_num = 0
        self._messages = {}
        self._local = SortedDict()
        self._remote = SortedDict()
        self._config = None

    def incr_seq_num(self, remote=False):
        if remote:
            self._remote_seq_num += 1
            return self._remote_seq_num
        else:
            self._local_seq_num += 1
            return self._local_seq_num

    def get_seq_num(self, remote=False):
        if remote:
            return self._remote_seq_num
        else:
            return self._local_seq_num

    def set_seq_num(self, seq_num, remote=False):
        if remote:
            self._remote_seq_num = seq_num
        else:
            self._local_seq_num = seq_num

    def store_message(self, msg, remote=False):
        seq_num = msg.get(34)
        self._messages[msg.uid] = msg.encode()
        if remote:
            self._remote[seq_num] = msg.uid
        else:
            self._local[seq_num] = msg.uid

    def get_message(self, uid):
        return self._messages.get(uid)

    def get_messages(self, keys=None):
        if keys:
            return {k: self._messages[k] for k in keys}
        else:
            return self._messages

    def get_messages_by_seq_num(self, remote=False):
        uids_by_seq = self._local
        if remote:
            uids_by_seq = self._remote
        return SortedDict({
            seq_num: self._messages[uid]
            for seq_num, uid
            in uids_by_seq
        })

    def new_session(self):
        self._messages = {}
        self._local = SortedDict()
        self._remote = SortedDict()
        self._config = None

    def store_config(self, conf):
        self._config = conf

    def get_config(self):
        return self._config


class FixRedisStore(FixStore):
    def __init__(self, **options):
        self.redis = redis.StrictRedis(
            host='127.0.0.1', port=6379, db=0, socket_timeout=5)
        self.conf = options.get('conf',  config.get_config_from_env())

    def get(self, key):
        res = self.redis.get(key)
        if res is not None:
            return res.decode()
        return None

    @staticmethod
    def decode_message(msg, uid=None):
        parser = fp.FixParser()
        parser.append_buffer(msg)
        return parser.get_message(uid)

    def incr_seq_num(self, remote=False):
        key = 'seq_num_local'
        if remote:
            key = 'seq_num_remote'
        return self.redis.incr(key)

    def set_seq_num(self, seq_num, remote=False):
        key = 'seq_num_local'
        if remote:
            key = 'seq_num_remote'
        self.redis.set(key, str(seq_num))

    def get_seq_num(self, remote=False):
        key = 'seq_num_local'
        if remote:
            key = 'seq_num_remote'
        return self.redis.get(key)

    def store_message(self, msg, remote=False):
        direction = 'remote' if remote else 'local'
        seq_num = msg.get(34)
        self.redis.hset('messages', msg.uid, msg.encode())
        self.redis.zadd(direction, int(seq_num), msg.uid)
        self.redis.zadd('messages_by_time', time.time(), msg.uid)

    def get_message(self, uid):
        msg = self.redis.hget('messages', uid)
        return self.decode_message(msg, uid)

    def get_messages(self, keys=None):
        if keys:
            msgs = self.redis.hmget('messages', *keys)
            msgs = dict(zip(keys, msgs))
        else:
            msgs = self.redis.hgetall('messages')
        return {uid: self.decode_message(msg, uid.decode()) for uid, msg in msgs.items()}

    def get_messages_by_seq_num(self, remote=False):
        direction = 'remote' if remote else 'local'
        uids_by_seq_num = self.redis.zrange(
            direction, start=0, end=-1, withscores=True)
        msgs = self.get_messages(keys=[uid for uid, _ in uids_by_seq_num])
        return SortedDict({
            seq_num: msgs[uid]
            for uid, seq_num
            in uids_by_seq_num
        })

    def get_messages_by_time(self):
        uids_by_time = self.redis.zrange(
            'messages_by_time', start=0, end=-1, withscores=True)
        msgs = self.get_messages(keys=[uid for uid, _ in uids_by_time])
        return SortedDict({
            timestamp: msgs[uid]
            for uid, timestamp
            in uids_by_time
        })

    def store_config(self, conf):
        jsoned = json.dumps(conf)
        self.redis.set('config', jsoned)

    def get_config(self):
        conf = self.redis.get('config')
        return json.loads(conf.decode())

    def new_session(self):
        for key in ['messages', 'received', 'sent', 'messages_by_time']:
            self.redis.delete(key)
        self.set_seq_num(0)
