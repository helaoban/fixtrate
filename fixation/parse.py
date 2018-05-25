import simplefix
from .message import Message


class FixParser(simplefix.FixParser):

    def __init__(self, config):
        super().__init__()
        self.config = config

    def get_message(self):
        msg = super().get_message()
        new_msg = Message(config=self.config)
        new_msg.begin_string = msg.begin_string
        new_msg.message_type = msg.message_type
        new_msg.pairs = msg.pairs
        new_msg.header_index = msg.header_index
        return new_msg

    @classmethod
    def parse(cls, raw_message, config):
        parser = cls(config=config)
        parser.append_buffer(raw_message)
        msg = parser.get_message()
        return msg
