import sys
import uuid

import simplefix
from fixation import utils, constants as fc


@utils.monkeypatch_module(simplefix.message)
def fix_val(value):

    # Enum support
    try:
        value = value.value
    except AttributeError:
        pass

    if isinstance(value, (bytes, str,)):
        if len(value) < 1:
            raise ValueError('FIX value cannot be empty!')
        try:
            value = value.encode()
        except AttributeError:
            pass
        return value
    else:
        return bytes(str(value), 'ASCII')


@utils.monkeypatch_module(simplefix.message)
def fix_tag(value):
    """Make a FIX tag value from string, bytes, integer, or Enum"""

    # Enum support
    try:
        value = value.value
    except AttributeError:
        pass

    if sys.version_info[0] == 2:
        return bytes(value)
    else:
        if type(value) == bytes:
            return value
        elif type(value) == str:
            return value.encode('ASCII')
        return str(value).encode('ASCII')


class FixMessage(simplefix.FixMessage):

    def __init__(self, uid=None):
        super().__init__()
        self.uid = uid or str(uuid.uuid4())

    def get(self, tag, nth=1, raw=False):
        val = super().get(tag, nth=nth)
        if not val:
            return None
        if not raw:
            return val.decode()
        return val

    def to_decoded_pairs(self):
        return [(fc.FixTag.FIX42(tag).name, val.decode()) for tag, val in self]

    def to_json(self):

        msg_type = self.get(fc.FixTag.FIX42.MsgType)
        msg_type = fc.FixMsgType(msg_type)
        seq_num = int(self.get(fc.FixTag.FIX42.MsgSeqNum))

        return {
            'uid': self.uid,
            'seqNum': seq_num,
            'msgType': msg_type,
            'msgTypeName': msg_type.name,
            'pairs': self.to_decoded_pairs(),
            'raw': self.__str__()
        }