import asyncio as aio
from types import TracebackType
import typing as t
import typing_extensions as te


def is_coro(func):
    return func.__code__.co_flags & (2 << 6) == 128


async def wait_sync_async(func, *args, **kwargs):
    if is_coro(func):
        return await func(*args, **kwargs)
    return func(*args, **kwargs)


async def cancel_suppress(*tasks: aio.Task):
    for task in tasks:
        task.cancel()
        try:
            await task
        except aio.CancelledError:
            pass


class SupportsClose(te.Protocol):

    async def close(self) -> None:
        pass


ACMRetType = t.TypeVar("ACMRetType", bound=SupportsClose)

if t.TYPE_CHECKING:
    ValidCoro = t.Coroutine[aio.Future[t.Any], None, ACMRetType]
    ExitRetType = t.TypeVar("ExitRetType")
    ExitCallable = t.Callable[[
        ExitRetType,
        t.Optional[t.Type[BaseException]],
        t.Optional[BaseException],
        t.Optional[TracebackType],
    ], t.Awaitable[t.Optional[bool]]]


class AwaitableContextManager(
    t.Coroutine[t.Any, t.Any, ACMRetType],
    t.Generic[ACMRetType],
):

    __slots__ = ('_coro', '_on_exit', '_resp')

    def __init__(
        self,
        coro: "ValidCoro",
        on_exit: "t.Optional[ExitCallable[ACMRetType]]" = None,
    ) -> None:
        self._coro = coro
        self._on_exit = on_exit

    def send(self, arg: None) -> "aio.Future[t.Any]":
        return self._coro.send(arg)

    def throw(self, arg: BaseException) -> None:  # type: ignore
        self._coro.throw(arg)  # type: ignore

    def close(self) -> None:
        return self._coro.close()

    def __await__(self) -> "t.Generator[t.Any, None, ACMRetType]":
        ret = self._coro.__await__()
        return ret

    def __iter__(self) -> "t.Generator[t.Any, None, ACMRetType]":
        return self.__await__()

    async def __aenter__(self) -> "ACMRetType":
        self._resp = await self._coro
        return self._resp

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        if self._on_exit:
            return await wait_sync_async(
                self._on_exit, self._resp, exc_type, exc, tb)
        else:
            await self._resp.close()
            return False
