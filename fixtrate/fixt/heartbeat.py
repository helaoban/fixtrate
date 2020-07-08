import typing as t
import typing_extensions as te
from collections import OrderedDict
import datetime as dt
from decimal import Decimal

from fixtrate.message import FixMessage
from .types import FixTag as FT, TYPE_MAP
from .validate import validate, convert, cast as _cast


class Heartbeat(FixMessage):

    _msg_type = "0"

    _fields = OrderedDict({
        FT.TestReqID: False,
    })

    def get(self, tag: te.Literal[FT.TestReqID]) -> t.Optional[str]:
        val = self.get_raw(tag)
        if val is None:
            return None
        return validate(TYPE_MAP[tag], val)

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.TestReqID],
        val: t.Optional[str],
    ) -> None:
        ...

    def append(self, tag: FT, val: t.Any):  # NOQA
        if tag is FT.TestReqID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        else:
            raise ValueError(f"{tag} is not a valid FIX tag")
        self.append_pair(tag, converted)

    @classmethod
    def cast(cls, msg: FixMessage) -> "Heartbeat":
        return _cast(cls, msg)
