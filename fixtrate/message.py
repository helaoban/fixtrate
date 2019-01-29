from dateutil import parser as dateparser
import pytz
import simplefix
from fixtrate import constants as fc


class FixMessage(simplefix.FixMessage):

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

    @property
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

    @property
    def version(self):
        """
        Read-only property. Returns the FIX version for this message..

        :return: :class:`~fixtrate.contants.FixVersion` or `None`
        :raises: `ValueError` if version string is not a valid FIX version or
            if BeginString<8> is not set on message..
        """
        begin_str = self.get(8)
        if begin_str is not None:
            return fc.FixVersion(begin_str)
        raise ValueError('BeginString<8> was not set on this message, '
                         'so version could not be determined')

    @property
    def msg_type(self):
        """
        Read-only property. Returns the value of the message's
        MsgType<35> field, or `None` if MsgType<35> is not set.

        :return: :class:`~fixtrate.constants.FixMsgType` or `None`
        """
        _msg_type = self.get(35)
        if _msg_type is not None:
            _msg_type = fc.FixMsgType(_msg_type)
        return _msg_type

    @property
    def sending_time(self):
        send_time = self.get(52)
        if send_time is None:
            return send_time

        send_time = dateparser.parse(send_time)
        if send_time.tzinfo is None:
            send_time.replace(tzinfo=pytz.utc)

        return send_time

    @property
    def is_duplicate(self):
        """
        Read-only property. Returns `True` if the PossDupFlag is set
        to 'Y'.

        :return: bool
        """
        return self.get(43) == fc.PossDupFlag.YES

    def get(self, tag, nth=1, raw=False):
        val = super().get(tag, nth=nth)
        if not val:
            return None
        if not raw:
            return val.decode()
        return val

    def to_decoded_pairs(self):
        """
        Return message pairs as list of decoded ``(tag, value)``
        tuples.

        :return: list of ``(tag, value)`` tuples.
        """
        tags = getattr(fc.FixTag, self.version.name)
        pairs = []
        for tag, val in self:
            try:
                tag = tags(tag).name
            except ValueError:
                tag = 'Unknown Tag <{}>'.format(tag)
            pairs.append((tag, val.decode()))
        return pairs

    def to_dict(self):
        """
        Returns dictionary representation of message.

        :return: `dict`
        """
        msg_type = self.get(35)
        seq_num = self.get(34)
        if seq_num:
            seq_num = int(seq_num)

        return {
            'version': self.version,
            'seq_num': seq_num,
            'msg_type': msg_type,
            'pairs': self.to_decoded_pairs(),
            'raw': self.__str__()
        }

    @classmethod
    def from_raw(cls, raw_message):
        parser = simplefix.FixParser()
        parser.append_buffer(raw_message)
        msg = parser.get_message()
        if msg is None:
            return msg
        converted = FixMessage()
        for tag, val in msg:
            converted.append_pair(tag, val)
        return converted
