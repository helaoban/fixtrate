import typing as t
import typing_extensions as te
from collections import OrderedDict
import datetime as dt
from decimal import Decimal

from fixtrate.message import FixMessage
from .types import FixTag as FT, TYPE_MAP
from .validate import validate, convert, cast as _cast


class AllocationInstructionAck(FixMessage):

    _msg_type = "P"

    _fields = OrderedDict({
        FT.ClientID: False,
        FT.ExecBroker: False,
        FT.AllocID: True,
        FT.TradeDate: True,
        FT.TransactTime: False,
        FT.AllocStatus: True,
        FT.AllocRejCode: False,
        FT.Text: False,
        FT.EncodedTextLen: False,
        FT.EncodedText: False,
    })

    def __init__(
        self,
        alloc_id: str,
        trade_date: dt.date,
        alloc_status: int,
    ) -> None:
        super().__init__()
        self.append_pair(35, self._msg_type)
        self.append_pair(
            FT.AllocID,
            convert("STRING", alloc_id),
        )
        self.append_pair(
            FT.TradeDate,
            convert("LOCALMKTDATE", trade_date),
        )
        self.append_pair(
            FT.AllocStatus,
            convert("INT", alloc_status),
        )

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.AllocID]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TradeDate]) -> dt.date:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.AllocStatus]) -> int:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ClientID]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ExecBroker]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TransactTime]) -> t.Optional[dt.datetime]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.AllocRejCode]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.Text]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.EncodedTextLen]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.EncodedText]) -> t.Optional[str]:
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
        tag: te.Literal[FT.ClientID],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.ExecBroker],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.AllocID],
        val: str,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.TradeDate],
        val: dt.date,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.TransactTime],
        val: t.Optional[dt.datetime],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.AllocStatus],
        val: int,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.AllocRejCode],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.Text],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.EncodedTextLen],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.EncodedText],
        val: t.Optional[str],
    ) -> None:
        ...

    def append(self, tag: FT, val: t.Any):  # NOQA
        if tag is FT.ClientID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.ExecBroker:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.AllocID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.TradeDate:
            assert isinstance(val, dt.date)
            converted = convert("LOCALMKTDATE", val)
        elif tag is FT.TransactTime:
            assert isinstance(val, dt.datetime)
            converted = convert("UTCTIMESTAMP", val)
        elif tag is FT.AllocStatus:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.AllocRejCode:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.Text:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.EncodedTextLen:
            assert isinstance(val, int)
            converted = convert("LENGTH", val)
        elif tag is FT.EncodedText:
            assert isinstance(val, str)
            converted = convert("DATA", val)
        else:
            raise ValueError(f"{tag} is not a valid FIX tag")
        self.append_pair(tag, converted)

    @classmethod
    def cast(cls, msg: FixMessage) -> "AllocationInstructionAck":
        return _cast(cls, msg)