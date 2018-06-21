import redis
from simplefix import FixParser


class FixStore(object):

    def increment_local_sequence_number(self):
        raise NotImplementedError

    def increment_remote_sequence_number(self):
        raise NotImplementedError

    def get_local_sequence_number(self):
        raise NotImplementedError

    def get_remote_sequence_number(self):
        raise NotImplementedError

    def set_local_sequence_number(self, new_sequence_number):
        raise NotImplementedError

    def set_remote_sequence_number(self, new_sequence_number):
        raise NotImplementedError

    def reset_local_sequence_number(self):
        raise NotImplementedError

    def reset_remote_sequence_number(self):
        raise NotImplementedError

    def store_sent_message(self, sequence_number, message):
        raise NotImplementedError

    def store_received_message(self, sequence_number, message):
        raise NotImplementedError

    def get_sent_message_by_sequence(self, sequence_number):
        raise NotImplementedError

    def get_sent_message_by_index(self, sequence_number):
        raise NotImplementedError

    def get_sent_messages(self):
        raise NotImplementedError

    def get_received_message_by_sequence(self, sequence_number):
        raise NotImplementedError

    def get_received_message_by_index(self, sequence_number):
        raise NotImplementedError

    def get_received_messages(self):
        raise NotImplementedError

    def add_order(self, order_id, order):
        raise NotImplementedError

    def remove_order(self, order_id):
        raise NotImplementedError


class FixMemoryStore(FixStore):

    def __init__(self):
        self._local_sequence_number = 0
        self._remote_sequence_number = 0
        self._sent_messages = {}
        self._received_messages = {}
        self._orders = {}

    def increment_local_sequence_number(self):
        self._local_sequence_number += 1
        return self._local_sequence_number

    def increment_remote_sequence_number(self):
        self._remote_sequence_number += 1
        return self._remote_sequence_number

    def get_local_sequence_number(self):
        return self._local_sequence_number

    def get_remote_sequence_number(self):
        return self._remote_sequence_number

    def set_local_sequence_number(self, new_sequence_number):
        self._local_sequence_number = new_sequence_number

    def set_remote_sequence_number(self, new_sequence_number):
        self._remote_sequence_number = new_sequence_number

    def reset_local_sequence_number(self):
        self._local_sequence_number = 0

    def reset_remote_sequence_number(self):
        self._remote_sequence_number = 0

    def store_sent_message(self, sequence_number, message):
        self._sent_messages[sequence_number] = message

    def store_received_message(self, sequence_number, message):
        self._received_messages[sequence_number] = message

    def get_sent_message_by_sequence(self, sequence_number):
        return self._sent_messages.get(sequence_number)

    def get_sent_message_by_index(self, index):
        messages = [v for _, v in sorted(self._sent_messages.items())]
        return messages[index]

    def get_sent_messages(self):
        return [(int(k), v) for k, v in sorted(self._sent_messages.items())]

    def get_received_message_by_sequence(self, sequence_number):
        return self._received_messages.get(sequence_number)

    def get_received_message_by_index(self, index):
        messages = [v for _, v in sorted(self._received_messages.items())]
        return messages[index]

    def get_received_messages(self):
        return [(int(k), v) for k, v in sorted(self._received_messages.items())]

    def add_order(self, order_id, order):
        self._orders[order_id] = order

    def remove_order(self, order_id):
        del self._orders[order_id]


class FixRedisStore(FixStore):
    def __init__(self, **options):
        self.redis = redis.StrictRedis(host='127.0.0.1', port=6379, db=0, socket_timeout=5)

    @staticmethod
    def decode_message(message, parser=None):
        parser = parser or FixParser()
        parser.append_buffer(message)
        return parser.get_message()

    def decode_messages(self, messages):
        parser = FixParser()
        decoded_messages = []
        for m in messages:
            decoded = self.decode_message(m, parser=parser)
            decoded_messages.append(decoded)
        return decoded_messages

    def increment_local_sequence_number(self):
        return self.redis.incr('local_sequence_number')

    def increment_remote_sequence_number(self):
        return self.redis.incr('remote_sequence_number')

    def set_local_sequence_number(self, new_sequence_number):
        self.redis.set('local_sequence_number', str(new_sequence_number))

    def set_remote_sequence_number(self, new_sequence_number):
        self.redis.set('remote_sequence_number', str(new_sequence_number))

    def reset_local_sequence_number(self):
        return self.redis.set('local_sequence_number', '0')

    def reset_remote_sequence_number(self):
        return self.redis.set('remote_sequence_number', '0')

    def store_sent_message(self, sequence_number, message):
        self.redis.zadd('sent_messages', sequence_number, message)

    def store_received_message(self, sequence_number, message):
        self.redis.zadd('received_messages', sequence_number, message)

    def get_sent_message(self, sequence_number):
        msg = self.redis.zrangebyscore(
            name='sent_messages',
            min=sequence_number,
            max=sequence_number,
            withscores=True
        )
        return self.decode_message(msg)

    def get_sent_messages(self):
        messages = self.redis.zrange(name='received_messages', start=0, end=-1)
        return dict(zip(messages.keys(), self.decode_messages(messages)))

    def get_received_message(self, sequence_number):
        msg = self.redis.zrangebyscore(
            name='received_messages',
            min=sequence_number,
            max=sequence_number,
            withscores=True
        )
        return self.decode_message(msg)

    def get_received_messages(self):
        messages = self.redis.zrange(name='received_messages', start=0, end=-1)
        return dict(zip(messages.keys(), self.decode_messages(messages)))

    def get_local_sequence_number(self):
        sequence_number = self.redis.get('local_sequence_number')
        if sequence_number is None:
            self.reset_local_sequence_number()
            return self.get_local_sequence_number()
        return sequence_number

    def get_remote_sequence_number(self):
        return int(self.redis.get('remote_sequence_number'))

    def add_order(self, order_id, order):
        self.redis.hset(name='orders', key=order_id, value=order)

    def remove_order(self, order_id):
        self.redis.hdel('orders', order_id)
