from . import constants as fix


class FIXError(Exception):
    """A FIX error occured"""
    pass


class SessionError(FIXError):
    """A FIX session-level error occured"""


class FIXAuthenticationError(FIXError):
    """Unablet to authenticate client"""


class DuplicateSessionError(FIXAuthenticationError):
    """A connection is already bound to this session."""

    def __init__(self):
        msg = 'A connection is already bound to this session.'
        super().__init__(msg)


class SequenceGapError(FIXError):
    """
    A sequence gap occured (remote sequence number
    is greater than expected).
    """
    def __init__(self, fix_msg, gap):
        expected = fix_msg.seq_num - gap
        greater_or_lower = 'greater' if gap > 0 else 'lower'
        error = (
            'Remote sequence number is %s than '
            'expected, expected %s but got %s'
            '' % (greater_or_lower, expected, fix_msg.seq_num)
        )
        super().__init__(error)
        self.fix_msg = fix_msg
        self.gap = gap
        self.expected = expected


class FatalSequenceGapError(SequenceGapError):
    """
    A fatal sequence gap occured (remote sequence number
    is lower than expected).
    """


class FixRejectionError(FIXError):
    """ Reject<3> message received."""
    def __init__(self, rej_msg, reason):
        self.rej_msg = rej_msg
        self.reason = reason
        msg = 'Peer rejected message: %s' % reason
        super().__init__(msg)


class UnsupportedVersion(FIXError):
    """ Unsupported FIX version"""
    pass


class InvalidFixDictTag(FIXError):
    """ Tag specified in FIX XML dictionary is not a valid FIX tag"""
    pass


class InvalidFIXVersion(FIXError):
    def __init__(self, version):
        super().__init__(
            '{} is not a valid FIX version'.format(version))


class InvalidMessageError(FIXError):
    """An invalid message was received"""

    def __init__(self, msg, fix_msg, tag, reject_type):
        self.fix_msg = fix_msg
        self.tag = tag
        self.reject_type = reject_type
        super().__init__(msg)


class MissingRequiredTagError(InvalidMessageError):
    """An required tag is missing"""
    reject_type = fix.SessionRejectReason.REQUIRED_TAG_MISSING

    def __init__(self, fix_msg, tag):
        self.fix_msg = fix_msg
        error = 'Missing required tag %s.' % tag
        super().__init__(error, fix_msg, tag, self.reject_type)


class IncorrectTagValueError(InvalidMessageError):
    """An invalid message was received"""
    reject_type = fix.SessionRejectReason.VALUE_IS_INCORRECT

    def __init__(self, fix_msg, tag, expected, actual):
        self.fix_msg = fix_msg
        error = 'Expected %s for tag %s, instead got %s' % (
            expected, tag, actual)
        super().__init__(error, fix_msg, tag, self.reject_type)


class InvalidTypeError(InvalidMessageError):
    """Incorrect data type for value"""
    reject_type = fix.SessionRejectReason.INCORRECT_DATA_FORMAT_FOR_VALUE

    def __init__(self, fix_msg, tag, value, expected_type):
        self.fix_msg = fix_msg
        error = (
            '%s is not of a valid type for '
            'tag %s, expected type [%s]' % (
                value, tag, expected_type.__name__)
        )
        super().__init__(error, fix_msg, tag, self.reject_type)


class BindClosedError(RuntimeError):
    """Bind was closed while waiting for session"""
    def __init__(self):
        super().__init__('Bind was closed while waiting for session')


class UnresponsiveClientError(TimeoutError):
    """Did not receive a respone from the client in the alloted time"""

    def __init__(self):
        msg = (
            'Did not receive a respone from '
            'the client in the alloted time'
        )
        super().__init__(msg)
