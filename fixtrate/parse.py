import typing as t
import simplefix  # type: ignore
from .message import FixMessage


__all__ = ("FixParser", )


class FixParser:

    def __init__(self):
        self._parser = simplefix.FixParser()

    def get_message(self) -> t.Optional[FixMessage]:
        msg = self._parser.get_message()
        if msg is None:
            return None
        return FixMessage(msg)

    def append_buffer(self, buf: bytes) -> None:
        self._parser.append_buffer(buf)
