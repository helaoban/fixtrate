import json
import ipaddress
import struct
import uuid


class MixedClass(type):
    def __new__(mcs, name, bases, classdict):
        classinit = classdict.get('__init__')  # Possibly None.

        # define an __init__ function for the new class
        def __init__(self, *args, **kwargs):
            # call the __init__ functions of all the bases
            for base in type(self).__bases__:
                base.__init__(self, *args, **kwargs)
            # also call any __init__ function that was in the new class
            if classinit:
                classinit(self, *args, **kwargs)

        # add the local function to the new class
        classdict['__init__'] = __init__
        return type.__new__(mcs, name, bases, classdict)


def validate_ip_address(address):
    ipaddress.ip_address(address)


def validate_port(port):
    port = str(port)
    if not port.isdigit():
        raise ValueError
    if int(port) not in range(1, 65535 + 1):
        raise ValueError


def validate_option(key, options, label):

    val = options.get(key)
    if val is None:
        raise ValueError(
            'Invalid {} type, expected one of: {}'
            ''.format(label, options)
        )
    return val


def gen_uuid():
    return str(uuid.uuid4())


def monkeypatch_module(mod):
    def decorator(func):
        setattr(mod, func.__name__, func)
        return func
    return decorator


def is_coro(func):
    return func.__code__.co_flags & (2 << 6) == 128


def parse_rpc_message(buf):
    if len(buf) < 4:
        return None, buf

    rlen = int(struct.unpack('i', buf[:4])[0])
    buf = buf[4:]

    if len(buf) < rlen:
        return None, buf

    return buf[:rlen], buf[rlen:]


def pack_rpc_message(message):
    message = {
        'jsonrpc': '2.0',
        **message
    }
    message = json.dumps(message).encode()
    mlen = struct.pack('i', len(message))
    return mlen + message


def print_to_console(val):
    print('\n{}'.format(val))
