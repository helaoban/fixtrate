import asyncio as aio

def is_coro(func):
    return func.__code__.co_flags & (2 << 6) == 128


async def maybe_await(func, *args, **kwargs):
    if is_coro(func):
        return await func(*args, **kwargs)
    else:
        return func(*args, **kwargs)


class Sleeper:
    """Group sleep calls allowing instant cancellation of all
    from: https://stackoverflow.com/a/37251120
    """

    def __init__(self):
        self.tasks = set()

    async def sleep(self, delay, result=None):
        coro = aio.sleep(delay, result=result)
        task = aio.ensure_future(coro)
        self.tasks.add(task)
        try:
            return await task
        except aio.CancelledError:
            return result
        finally:
            self.tasks.remove(task)

    def cancel_all_helper(self):
        "Cancel all pending sleep tasks"
        cancelled = set()
        for task in self.tasks:
            if task.cancel():
                cancelled.add(task)
        return cancelled

    async def cancel_all(self):
        "Coroutine cancelling tasks"
        cancelled = self.cancel_all_helper()
        try:
            await aio.wait(self.tasks)
        except ValueError:
            # TODO catching this from idempodence,
            # idiot fix for when this is called twice 
            # by accident (there must be a better way)
            pass
        self.tasks -= cancelled
        return len(cancelled)
