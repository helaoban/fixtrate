from collections import defaultdict
import uuid
import time
import typing as t
import logging
import threading

from sortedcontainers import SortedList  # type: ignore

from fix.message import FixMessage
from .base import FixStore


if t.TYPE_CHECKING:
    from fix.config import FixSessionConfig


__all__ = ("MemoryStore", )


logger = logging.getLogger(__name__)


def sortfunc(pair: t.Tuple[float, bytes]) -> float:
    return pair[0]


def parse_msg(raw_msg: bytes) -> FixMessage:
    msg = FixMessage.from_raw(raw_msg)
    if msg is None:
        raise RuntimeError(
            "Not able to parse fix msg from string")
    if msg.seq_num is None:
        raise RuntimeError(
            "Msg is missing seq num. Msg may be corrupted")
    return msg


def _make_store() -> dict:
    return {
        "msgs": dict(),
        "msgs_by_time": SortedList(key=sortfunc),
        "msgs_sent": SortedList(key=sortfunc),
        "msgs_received": SortedList(key=sortfunc),
        "seq_num_local": 0,
        "seq_num_remote": 1,
    }


thread_locals = threading.local()
thread_locals.store_data = defaultdict(lambda: _make_store())


def get_store_data():
    return thread_locals.store_data


def reset_store_data():
    thread_locals.store_data.clear()


class MemoryStore(FixStore):

    def __init__(self, config: "FixSessionConfig") -> None:
        super().__init__(config)

    def _make_session_id(self) -> str:
        return ':'.join(filter(None, (
            self.config.version, self.config.sender,
            self.config.target, self.config.qualifier)))

    def _reset_store(self) -> None:
        session_id = self._make_session_id()
        thread_locals.store_data[session_id] = _make_store()

    def get_store(self) -> dict:
        session_id = self._make_session_id()
        return thread_locals.store_data[session_id]

    async def incr_local(self) -> int:
        key = "seq_num_local"
        store = self.get_store()
        store[key] = store[key] + 1
        return store[key]

    async def incr_remote(self) -> int:
        key = "seq_num_remote"
        store = self.get_store()
        store[key] = store[key] + 1
        return store[key]

    async def get_local(self) -> int:
        store = self.get_store()
        return store["seq_num_local"]

    async def get_remote(self) -> int:
        store = self.get_store()
        return store["seq_num_remote"]

    async def set_local(self, new_seq_num: int) -> None:
        store = self.get_store()
        store["seq_num_local"] = new_seq_num

    async def set_remote(self, new_seq_num: int) -> None:
        store = self.get_store()
        store["seq_num_remote"] = new_seq_num

    async def store_msg(self, *msgs: FixMessage):
        store = self.get_store()
        for msg in msgs:
            uid = str(uuid.uuid4())
            store_time = time.time()

            store["msgs"][uid] = msg.encode()

            is_sent = msg.get_raw(49) == self.config.sender
            suffix = "sent" if is_sent else "received"

            for key in ["msgs_by_time", f"msgs_{suffix}"]:
                store[key].add((store_time, uid))

    async def get_msgs(
        self,
        min: float = float("-inf"),
        max: float = float("inf"),
        limit: float = float("inf"),
        index: str = "by_time",
        sort: str = "ascending",
    ) -> t.AsyncGenerator[FixMessage, None]:
        store = self.get_store()

        msgs_ids = store[f"msgs_{index}"]

        num_msgs = len(msgs_ids)

        if sort == "descending":
            msgs_ids = reversed(msgs_ids)

        # This is to iterate over the exact number of messages
        # at the time of the generator invocation.
        # msgs_ids can grow while iterating over this list,
        # and we can get stuck in an inifite loop if we iterate
        # over the list directly.

        for i, (_, uid) in enumerate(msgs_ids):
            if i == num_msgs or i == limit:
                break

            raw_msg = store["msgs"][uid]
            msg = parse_msg(raw_msg)

            if min <= msg.seq_num <= max:
                yield msg

    async def reset(self):
        self._reset_store()
        await self.set_local(1)
        await self.set_remote(2)

    async def close(self) -> None:
        pass
