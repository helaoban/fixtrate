import typing as t

from .fixt import data as VALUES


if t.TYPE_CHECKING:
    from .message import FixMessage
    TagType = t.Union[bytes, str, int]


BAD_VAL = VALUES.SessionRejectReason.VALUE_IS_INCORRECT
BAD_FORMAT = VALUES.SessionRejectReason.INCORRECT_DATA_FORMAT_FOR_VALUE


__all__ = (
    "FixError",
    "SessionError",
    "FIXAuthenticationError",
    "FatalSequenceGapError",
    "InvalidMessageError",
    "MissingRequiredTagError",
    "IncorrectTagValueError",
    "BindClosedError",
    "UnresponsiveClientError",
)


class FixError(Exception):
    """A FIX error occured"""
    pass


class SessionError(FixError):
    """A FIX session-level error occured"""


class SessionClosedError(FixError):
    """Session is closed"""


class FIXAuthenticationError(FixError):
    """Unablet to authenticate client"""


class FatalSequenceGapError(FixError):
    """
    A fatal sequence gap occured (remote sequence number
    is lower than expected).
    """
    def __init__(self, gap: int):
        self.gap = gap


class InvalidMessageError(FixError):
    """An invalid message was received"""

    def __init__(self, msg, fix_msg, tag, reject_type) -> None:
        self.fix_msg = fix_msg
        self.tag = tag
        self.reject_type = reject_type
        super().__init__(msg)


class MissingRequiredTagError(InvalidMessageError):
    """An required tag is missing"""
    reject_type = VALUES.SessionRejectReason.REQUIRED_TAG_MISSING

    def __init__(self, fix_msg: "FixMessage", tag: "TagType") -> None:
        self.fix_msg = fix_msg
        error = "Missing required tag %r." % tag
        super().__init__(error, fix_msg, tag, self.reject_type)


class IncorrectTagValueError(InvalidMessageError):
    """An invalid message was received"""
    reject_type = BAD_VAL

    def __init__(
        self,
        fix_msg: "FixMessage",
        tag: "TagType",
        expected: t.Any,
        actual: t.Any
    ) -> None:
        self.fix_msg = fix_msg
        error = "Expected %r for tag %r, instead got %r" % (
            expected, tag, actual)
        super().__init__(error, fix_msg, tag, self.reject_type)


class BindClosedError(RuntimeError):
    """Bind was closed while waiting for session"""
    def __init__(self) -> None:
        super().__init__('Bind was closed while waiting for session')


class UnresponsiveClientError(TimeoutError):
    """Did not receive a respone from the client in the alloted time"""

    def __init__(self) -> None:
        msg = (
            'Did not receive a respone from '
            'the client in the alloted time'
        )
        super().__init__(msg)
