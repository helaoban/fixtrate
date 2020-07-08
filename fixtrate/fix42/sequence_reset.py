import typing as t
import typing_extensions as te
from collections import OrderedDict
import datetime as dt
from decimal import Decimal

from fixtrate.message import FixMessage
from .types import FixTag as FT, TYPE_MAP
from .validate import validate, convert, cast as _cast


class SequenceReset(FixMessage):

    _msg_type = "4"

    _fields = OrderedDict({
        FT.GapFillFlag: False,
        FT.NewSeqNo: True,
    })

    def __init__(
        self,
        new_seq_no: int,
    ) -> None:
        super().__init__()
        self.append_pair(35, self._msg_type)
        self.append_pair(
            FT.NewSeqNo,
            convert("INT", new_seq_no),
        )

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.NewSeqNo]) -> int:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.GapFillFlag]) -> t.Optional[bool]:
        ...

    def get(self, tag: FT):  # NOQA
        is_required = self._fields[tag]
        val = self.get_raw(tag)
        if val is None:
            if is_required:
                raise ValueError
            return None
        return validate(TYPE_MAP[tag], val)

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.GapFillFlag],
        val: t.Optional[bool],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.NewSeqNo],
        val: int,
    ) -> None:
        ...

    def append(self, tag: FT, val: t.Any):  # NOQA
        if tag is FT.GapFillFlag:
            assert isinstance(val, bool)
            converted = convert("BOOLEAN", val)
        elif tag is FT.NewSeqNo:
            assert isinstance(val, int)
            converted = convert("INT", val)
        else:
            raise ValueError(f"{tag} is not a valid FIX tag")
        self.append_pair(tag, converted)

    @classmethod
    def cast(cls, msg: FixMessage) -> "SequenceReset":
        return _cast(cls, msg)