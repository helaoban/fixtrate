class SequenceGap(Exception):
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


class FatalSequenceGap(Exception):
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


class FixRejectionError(Exception):
    """ Reject<3> message received."""
    def __init__(self, reason):
        self._reason = reason

    @property
    def reason(self):
        """
        The rejection reason. From the Text<58> field of the reject message.
        """
        return self._reason


class UnsupportedVersion(Exception):
    """ Unsupported FIX version"""
    pass


class InvalidFixDictTag(Exception):
    """ Tag specified in FIX XML dictionary is not a valid FIX tag"""
    pass


class InvalidFIXVersion(Exception):
    def __init__(self, version):
        super().__init__(
            '{} is not a valid FIX version'.format(version))
