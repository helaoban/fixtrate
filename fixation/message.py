import sys
import uuid

import simplefix

from . import utils, constants as fc


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
        self._cache = {}

    @classmethod
    def from_pairs(cls, pairs):
        """ Create message from an iterable of ``(tag, value, is_header)`` tuples.

        :param pairs: An iterable of 3-tuple's ``(tag, value, is_header)``.
            `is_header` specifies whether the pair should be appended to the
            standard header or not.
        :return:
        """
        msg = cls()
        for tag, val, is_header in pairs:
            msg.append_pair(tag, val, header=is_header)
        return msg

    def _bust_cache(self, name):
        try:
            del self.__dict__[name]
        except KeyError:
            pass

    @utils.cached_property
    def seq_num(self):
        """
        Read-only property. Returns the value of MsgSeqNum<34>,
        or `None` if MsgSeqNum<34> is not set.

        :return: `int` or `None`
        """
        _seq_num = self.get(34)
        if _seq_num is not None:
            _seq_num = int(_seq_num)
        return _seq_num

    @utils.cached_property
    def msg_type(self):
        """
        Read-only property. Returns the value of the message's
        MsgType<35> field, or `None` if MsgType<35> is not set.

        :return: :class:`~fixation.constants.FixMsgType` or `None`
        """
        _msg_type = self.get(35)
        if _msg_type is not None:
            _msg_type = fc.FixMsgType(_msg_type)
        return _msg_type

    @utils.cached_property
    def is_duplicate(self):
        """
        Read-only property. Returns `True` if the PossDupFlag is set
        to 'Y'.

        :return: bool
        """
        poss_dup_flag = self.get(43)
        if poss_dup_flag is None:
            return False
        poss_dup_flag = fc.PossDupFlag(poss_dup_flag)
        return poss_dup_flag == fc.PossDupFlag.YES

    def get(self, tag, nth=1, raw=False):
        val = super().get(tag, nth=nth)
        if not val:
            return None
        if not raw:
            return val.decode()
        return val

    def append_pair(self, tag, value, header=False):
        super().append_pair(tag, value, header=header)
        # TODO need to guarantee that tag is an int, or else
        # there is posibility of missing a cache clear, which could
        # be really dangerous
        if tag == 34:
            self._bust_cache('seq_num')
        if tag == 35:
            self._bust_cache('msg_type')

    def to_decoded_pairs(self):
        """
        Return message pairs as list of decoded ``(tag, value)``
         tuples.

        :return: list of ``(tag, value)`` tuples.
        """
        pairs = []
        for tag, val in self:
            try:
                tag = fc.FixTag.FIX42(tag).name
            except ValueError:
                tag = 'Unknown Tag <{}>'.format(tag)
            pairs.append((tag, val.decode()))
        return pairs

    def to_json(self):
        """
        Return message as dictionary suitable for encoding to JSON.

        :return: `dict`
        """

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