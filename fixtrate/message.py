import datetime as dt
import typing as t

import simplefix as sf
from .fixt import data as VALUES
from .fixt.types import FixTag as TAGS


__all__ = ("FixMessage", )

MT = VALUES.MsgType

ADMIN_MESSAGES = {
    MT.LOGON,
    MT.LOGOUT,
    MT.HEARTBEAT,
    MT.TEST_REQUEST,
    MT.RESEND_REQUEST,
    MT.SEQUENCE_RESET,
}


if t.TYPE_CHECKING:
    TagType = t.Union[bytes, str, int]


class FixMessage:
    _fields: t.Dict[str, bool] = {}
    _msg: sf.FixMessage

    def __init__(
        self,
        msg: t.Optional[sf.FixMessage] = None
    ) -> None:
        self._msg = msg or sf.FixMessage()

    def __str__(self) -> str:
        return str(self._msg)

    def __contains__(self, item: "TagType") -> bool:
        return item in self._msg

    def __iter__(self):
        return self._msg

    def append_pair(
        self,
        tag: "TagType",
        value: t.Any,
        header: bool = False,
    ) -> None:
        self._msg.append_pair(tag, value, header)

    def append_utc_timestamp(
        self,
        tag: "TagType",
        timestamp: t.Union[str, dt.datetime],
        precision: int = 6,
        header: bool = False,
    ) -> None:
        self._msg.append_utc_timestamp(
            tag, timestamp, precision, header)

    @property
    def seq_num(self) -> int:
        """
        Read-only property. Returns the value of MsgSeqNum<34>,
        or `None` if MsgSeqNum<34> is not set.

        :return: `int` or `None`
        """
        _seq_num = self._msg.get(TAGS.MsgSeqNum)
        if _seq_num is None:
            raise ValueError(
                f"Msg is missing seq number: Msg: {self}")
        return int(_seq_num)

    @property
    def version(self) -> str:
        """
        Read-only property. Returns the FIX version for this message..

        :return: :class:`~fix.contants.FixVersion` or `None`
        :raises: `ValueError` if version string is not a valid FIX version or
            if BeginString<8> is not set on message..
        """
        begin_str = self._msg.get(TAGS.BeginString)
        if begin_str is not None:
            return begin_str.decode()
        raise ValueError('BeginString<8> was not set on this message, '
                         'so version could not be determined')

    @property
    def msg_type(self) -> str:
        """
        Read-only property. Returns the value of the message's
        MsgType<35> field, or `None` if MsgType<35> is not set.
        """
        _msg_type = self._msg.get(TAGS.MsgType)
        if _msg_type:
            return _msg_type.decode()
        raise ValueError('MsgType<35> is not set on this message.')

    @property
    def is_duplicate(self) -> bool:
        """
        Read-only property. Returns `True` if the PossDupFlag is set
        to 'Y'.

        :return: bool
        """
        return self._msg.get(TAGS.PossDupFlag) == "Y"

    @property
    def is_admin(self) -> bool:
        """
        Read-only property. Returns `True` if the message is an admin
        message.

        :return: bool
        """
        return self.msg_type in ADMIN_MESSAGES

    def get_raw(
        self,
        tag: "TagType",
        nth: int = 1,
    ) -> t.Optional[str]:
        val = self._msg.get(str(tag), nth=nth)
        if val is None:
            return None
        return val.decode()

    def get_or_raise(
        self,
        tag: "TagType",
        nth: int = 1,
    ) -> str:
        val = self.get_raw(tag)
        if val is None:
            raise ValueError(f"{str(tag)} does not have a value set")
        return val

    def remove(self, tag: "TagType"):
        self._msg.remove(tag)

    def encode(self) -> bytes:
        return self._msg.encode()

    def to_decoded_pairs(self) -> t.List[t.Tuple[int, t.Any]]:
        """
        Return message pairs as list of decoded ``(tag, value)``
        tuples.

        :return: list of ``(tag, value)`` tuples.
        """
        tags = getattr(TAGS, self.version)
        pairs = []
        for tag, val in self:
            try:
                tag = tags(tag).name
            except ValueError:
                tag = 'Unknown Tag <{}>'.format(tag)
            pairs.append((tag, val.decode()))
        return pairs

    @classmethod
    def from_raw(cls, raw_message: bytes) -> "t.Optional[FixMessage]":
        parser = sf.FixParser()
        parser.append_buffer(raw_message)
        msg = parser.get_message()
        if msg is None:
            return None
        return cls(msg)

    @classmethod
    def from_pairs(
        cls,
        pairs: t.Iterable[t.Tuple[int, t.Any, bool]]
    ) -> "FixMessage":
        """
        Create message from an iterable of
        ``(tag, value, is_header)`` tuples.

        :param pairs: An iterable of 3-tuple's ``(tag, value, is_header)``.
            `is_header` specifies whether the pair should be appended to the
            standard header or not.
        :return:
        """
        msg = cls()
        for tag, val, is_header in pairs:
            msg.append_pair(tag, val, header=is_header)
        return msg
