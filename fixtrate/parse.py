import simplefix
from .message import FixMessage


class FixParser(simplefix.FixParser):

    @staticmethod
    def _convert(msg):
        converted = FixMessage()
        for tag, val in msg:
            converted.append_pair(tag, val)
        return converted

    def get_message(self):
        msg = super().get_message()
        if msg is None:
            return msg
        return self._convert(msg)
