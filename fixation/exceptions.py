class SequenceGap(Exception):
    def __init__(self, actual, expected):
        super().__init__('Sequence gap detected, expected {} '
                         'but got {}'.format(expected, actual))
        self.actual = actual
        self.expected = expected


class FatalSequenceError(Exception):
    def __init__(self, actual, expected):
        super().__init__('Remote sequence number is lower than expected, '
                         'expected {} but got {}'.format(expected, actual))
        self.actual = actual
        self.expected = expected


class ImproperlyConfigured(Exception):
    def __init__(self, errors):
        self.errors = errors


class FixRejection(Exception):
    def __init__(self, reason):
        self.reason = reason


class UnknownCommand(Exception):
    pass


class UnsupportedVersion(Exception):
    pass


class InvalidFixDictTag(Exception):
    pass


RPC_ERRORS = {}


def register_rpc_error(code):
    def decorator(cls):
        RPC_ERRORS[code] = cls
        cls.code = code
        return cls
    return decorator


class RPCError(Exception):
    def __init__(self, code, message, meaning):
        self.code = code
        self.message = message
        self.meaning = meaning


@register_rpc_error(-32700)
class RPCParseError(RPCError):
    def __init__(self):
        message = 'Parse error'
        meaning = 'Invalid JSON was received by the server. ' \
                  'An error occurred on the server while parsing the JSON text.'
        super().__init__(-32700, message, meaning)


@register_rpc_error(-32600)
class RPCInvalidRequest(RPCError):
    def __init__(self):
        message = 'Invalid Request'
        meaning = 'The JSON sent is not a valid Request object.'
        super().__init__(-32600, message, meaning)


@register_rpc_error(-32601)
class RPCMethodNotFound(RPCError):
    def __init__(self):
        message = 'Method not found'
        meaning = 'The method does not exist / is not available.'
        super().__init__(-32601, message, meaning)


@register_rpc_error(-32602)
class RPCInvalidParams(RPCError):
    def __init__(self):
        message = 'Invalid params'
        meaning = 'Invalid method parameter(s).'
        super().__init__(-32602, message, meaning)


@register_rpc_error(-32603)
class RPCInternalError(RPCError):
    def __init__(self):
        message = 'Internal error'
        meaning = 'Internal JSON-RPC error.'
        super().__init__(-32603, message, meaning)


@register_rpc_error(-32000)
class RPCCommandError(RPCError):
    def __init__(self):
        message = 'RPC command error'
        meaning = 'An exception was raised during server method call'
        super().__init__(-32000, message, meaning)


class RPCCouldNotConnectError(Exception):
    pass


class RPCBadConnectionError(Exception):
    pass
