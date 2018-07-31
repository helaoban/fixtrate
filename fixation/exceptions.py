class SequenceGap(Exception):
    def __init__(self, actual, expected):
        super().__init__('Sequence gap detected, expected {} '
                         'but got {}'.format(expected, actual))
        self.actual = actual
        self.expected = expected


class FatalSequenceGap(Exception):
    def __init__(self, actual, expected):
        super().__init__('Remote sequence number is lower than expected, '
                         'expected {} but got {}'.format(expected, actual))
        self.actual = actual
        self.expected = expected


class FixRejection(Exception):
    def __init__(self, reason):
        self.reason = reason


class UnsupportedVersion(Exception):
    pass


class InvalidFixDictTag(Exception):
    pass

