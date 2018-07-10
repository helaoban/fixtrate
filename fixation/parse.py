import simplefix
from fixation import message as fm


def _convert(msg):
    new_msg = fm.FixMessage()
    new_msg.begin_string = msg.begin_string
    new_msg.message_type = msg.message_type
    new_msg.pairs = msg.pairs
    new_msg.header_index = msg.header_index
    return new_msg


class FixParser(simplefix.FixParser):

    def __init__(self, config):
        super().__init__()
        self.config = config

    def get_message(self):
        msg = super().get_message()
        # return msg
        if msg is None:
            return
        return _convert(msg)

    @classmethod
    def parse(cls, raw_message, config=None, base=False):
        parser = cls(config=config)
        parser.append_buffer(raw_message)
        base_msg = parser.get_message()

        if base:
            return base_msg

        if config is None:
            raise ValueError('Config muse be provided unless base=True')

        return _convert(base_msg)
