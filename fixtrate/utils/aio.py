def is_coro(func):
    return func.__code__.co_flags & (2 << 6) == 128


async def maybe_await(func, *args, **kwargs):
    if is_coro(func):
        return await func(*args, **kwargs)
    else:
        return func(*args, **kwargs)
