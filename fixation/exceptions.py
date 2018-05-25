class SequenceGap(Exception):
    pass


class ImproperlyConfigured(Exception):
    def __init__(self, errors):
        self.errors = errors


class FixRejection(Exception):
    def __init__(self, reason):
        self.reason = reason
