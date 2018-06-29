import simplefix
from . import message


class FixParser(simplefix.FixParser):

    def __init__(self, config):
        super().__init__()
        self.config = config

    # def get_message(self):
    #     msg = super().get_message()
    #     return msg
    #     # if msg is None:
    #     #     return
    #     # new_msg = message.Message(config=self.config)
    #     # new_msg.begin_string = msg.begin_string
    #     # new_msg.message_type = msg.message_type
    #     # new_msg.pairs = msg.pairs
    #     # new_msg.header_index = msg.header_index
    #     # return new_msg

    @classmethod
    def parse(cls, raw_message, config=None, base=False):
        parser = cls(config=config)
        parser.append_buffer(raw_message)
        base_msg = parser.get_message()

        if base:
            return base_msg

        if config is None:
            raise ValueError('Config muse be provided unless base=True')

        new_msg = message.FixMessage(config=config)
        new_msg.begin_string = base_msg.begin_string
        new_msg.message_type = base_msg.message_type
        new_msg.pairs = base_msg.pairs
        new_msg.header_index = base_msg.header_index

        return new_msg
