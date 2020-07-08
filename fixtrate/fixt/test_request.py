import typing as t
import typing_extensions as te
from collections import OrderedDict
import datetime as dt
from decimal import Decimal

from fix.message import FixMessage
from .types import FixTag as FT, TYPE_MAP
from .validate import validate, convert, cast as _cast


class TestRequest(FixMessage):

    _msg_type = "1"

    _fields = OrderedDict({
        FT.TestReqID: True,
    })

    def __init__(
        self,
        test_req_id: str,
    ) -> None:
        super().__init__()
        self.append_pair(35, self._msg_type)
        self.append_pair(
            FT.TestReqID,
            convert("STRING", test_req_id),
        )

    def get(self, tag: te.Literal[FT.TestReqID]) -> str:
        val = self.get_raw(tag)
        if val is None:
            raise ValueError
        return validate(TYPE_MAP[tag], val)

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.TestReqID],
        val: str,
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
    def cast(cls, msg: FixMessage) -> "TestRequest":
        return _cast(cls, msg)