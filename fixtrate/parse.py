import simplefix
from .message import FixMessage

class FixParser(simplefix.FixParser):

    def _convert(msg):
        converted = FixMessage()
        for tag, val in msg:
            converted.append_pair(tag, val)
        return converted

    def get_message(self, uid=None):
        msg = super().get_message()
        if msg is None:
            return msg
        return _convert(msg)
