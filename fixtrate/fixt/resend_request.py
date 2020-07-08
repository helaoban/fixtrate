import typing as t
import typing_extensions as te
from collections import OrderedDict
import datetime as dt
from decimal import Decimal

from fixtrate.message import FixMessage
from .types import FixTag as FT, TYPE_MAP
from .validate import validate, convert, cast as _cast


class ResendRequest(FixMessage):

    _msg_type = "2"

    _fields = OrderedDict({
        FT.BeginSeqNo: True,
        FT.EndSeqNo: True,
    })

    def __init__(
        self,
        begin_seq_no: int,
        end_seq_no: int,
    ) -> None:
        super().__init__()
        self.append_pair(35, self._msg_type)
        self.append_pair(
            FT.BeginSeqNo,
            convert("SEQNUM", begin_seq_no),
        )
        self.append_pair(
            FT.EndSeqNo,
            convert("SEQNUM", end_seq_no),
        )

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.BeginSeqNo]) -> int:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.EndSeqNo]) -> int:
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
        tag: te.Literal[FT.BeginSeqNo],
        val: int,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.EndSeqNo],
        val: int,
    ) -> None:
        ...

    def append(self, tag: FT, val: t.Any):  # NOQA
        if tag is FT.BeginSeqNo:
            assert isinstance(val, int)
            converted = convert("SEQNUM", val)
        elif tag is FT.EndSeqNo:
            assert isinstance(val, int)
            converted = convert("SEQNUM", val)
        else:
            raise ValueError(f"{tag} is not a valid FIX tag")
        self.append_pair(tag, converted)

    @classmethod
    def cast(cls, msg: FixMessage) -> "ResendRequest":
        return _cast(cls, msg)