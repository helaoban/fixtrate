class FIXError(Exception):
    """A FIX error occured"""
    pass


class InvalidMessageError(FIXError):
    """An invalid message was received"""
    def __init__(self, fix_msg, tag, rej_type, reason):
        self.fix_msg = fix_msg
        self.tag = tag
        self.rej_type = rej_type
        self.reason = reason

        super().__init__(reason)


class SequenceGapError(FIXError):
    """
    A SequenceGap occured
    """
    def __init__(self, actual, expected):
        super().__init__('Sequence gap detected, expected {} '
                         'but got {}'.format(expected, actual))
        self._actual = actual
        self._expected = expected

    @property
    def actual(self):
        """ The sequence number of the offending message"""
        return self._actual

    @property
    def expected(self):
        """
        The excepted sequence number before offended message
        was received.
        """
        return self._expected


class FatalSequenceGapError(FIXError):
    """
    A fatal sequence gap occured (remote sequence number
    is lower than expected).
    """
    def __init__(self, actual, expected):
        super().__init__('Remote sequence number is lower than expected, '
                         'expected {} but got {}'.format(expected, actual))
        self._actual = actual
        self._expected = expected

    @property
    def actual(self):
        """ The sequence number of the offending message"""
        return self._actual

    @property
    def expected(self):
        """
        The excepted sequence number before offended message
        was received.
        """
        return self._expected


class FixRejectionError(FIXError):
    """ Reject<3> message received."""
    def __init__(self, reason):
        self._reason = reason
        super().__init__(reason)

    @property
    def reason(self):
        """
        The rejection reason. From the Text<58> field of the reject message.
        """
        return self._reason


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
