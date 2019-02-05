import ipaddress
import uuid


def chunked(iterator, size):
    chunk = []
    for item in iterator:
        chunk.append(item)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


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


async def maybe_await(func, *args, **kwargs):
    if is_coro(func):
        return await func(*args, **kwargs)
    else:
        return func(*args, **kwargs)


def print_to_console(val):
    print('\n{}'.format(val))


def raise_invalid_option(name, valid_options):
    raise ValueError(
        '{} must be one of: {}'
        ''.format(name, list_members(valid_options))
    )


def list_members(interable):
    return '|'.join(o for o in interable)


class cached_property:
    """
    See https://github.com/django/django/blob/master/django/utils/functional.py#L19

    Decorator that converts a method with a single self argument into a
    property cached on the instance.
    Optional ``name`` argument allows you to make cached properties of other
    methods. (e.g.  url = cached_property(get_absolute_url, name='url') )
    """
    def __init__(self, func, name=None):
        self.func = func
        self.__doc__ = getattr(func, '__doc__')
        self.name = name or func.__name__

    def __get__(self, instance, cls=None):
        """
        Call the function and put the return value in instance.__dict__ so that
        subsequent attribute access on the instance returns the cached value
        instead of calling cached_property.__get__().
        """
        if instance is None:
            return self
        res = instance.__dict__[self.name] = self.func(instance)
        return res
