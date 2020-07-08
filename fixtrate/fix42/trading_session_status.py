import typing as t
import typing_extensions as te
from collections import OrderedDict
import datetime as dt
from decimal import Decimal

from fixtrate.message import FixMessage
from .types import FixTag as FT, TYPE_MAP
from .validate import validate, convert, cast as _cast


class TradingSessionStatus(FixMessage):

    _msg_type = "h"

    _fields = OrderedDict({
        FT.TradSesReqID: False,
        FT.TradingSessionID: True,
        FT.TradSesMethod: False,
        FT.TradSesMode: False,
        FT.UnsolicitedIndicator: False,
        FT.TradSesStatus: True,
        FT.TradSesStartTime: False,
        FT.TradSesOpenTime: False,
        FT.TradSesPreCloseTime: False,
        FT.TradSesCloseTime: False,
        FT.TradSesEndTime: False,
        FT.TotalVolumeTraded: False,
        FT.Text: False,
        FT.EncodedTextLen: False,
        FT.EncodedText: False,
    })

    def __init__(
        self,
        trading_session_id: str,
        trad_ses_status: int,
    ) -> None:
        super().__init__()
        self.append_pair(35, self._msg_type)
        self.append_pair(
            FT.TradingSessionID,
            convert("STRING", trading_session_id),
        )
        self.append_pair(
            FT.TradSesStatus,
            convert("INT", trad_ses_status),
        )

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TradingSessionID]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TradSesStatus]) -> int:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TradSesReqID]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TradSesMethod]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TradSesMode]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.UnsolicitedIndicator]) -> t.Optional[bool]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TradSesStartTime]) -> t.Optional[dt.datetime]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TradSesOpenTime]) -> t.Optional[dt.datetime]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TradSesPreCloseTime]) -> t.Optional[dt.datetime]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TradSesCloseTime]) -> t.Optional[dt.datetime]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TradSesEndTime]) -> t.Optional[dt.datetime]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TotalVolumeTraded]) -> t.Optional[Decimal]:
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
        tag: te.Literal[FT.TradSesReqID],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.TradingSessionID],
        val: str,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.TradSesMethod],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.TradSesMode],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.UnsolicitedIndicator],
        val: t.Optional[bool],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.TradSesStatus],
        val: int,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.TradSesStartTime],
        val: t.Optional[dt.datetime],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.TradSesOpenTime],
        val: t.Optional[dt.datetime],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.TradSesPreCloseTime],
        val: t.Optional[dt.datetime],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.TradSesCloseTime],
        val: t.Optional[dt.datetime],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.TradSesEndTime],
        val: t.Optional[dt.datetime],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.TotalVolumeTraded],
        val: t.Optional[Decimal],
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
        if tag is FT.TradSesReqID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.TradingSessionID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.TradSesMethod:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.TradSesMode:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.UnsolicitedIndicator:
            assert isinstance(val, bool)
            converted = convert("BOOLEAN", val)
        elif tag is FT.TradSesStatus:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.TradSesStartTime:
            assert isinstance(val, dt.datetime)
            converted = convert("UTCTIMESTAMP", val)
        elif tag is FT.TradSesOpenTime:
            assert isinstance(val, dt.datetime)
            converted = convert("UTCTIMESTAMP", val)
        elif tag is FT.TradSesPreCloseTime:
            assert isinstance(val, dt.datetime)
            converted = convert("UTCTIMESTAMP", val)
        elif tag is FT.TradSesCloseTime:
            assert isinstance(val, dt.datetime)
            converted = convert("UTCTIMESTAMP", val)
        elif tag is FT.TradSesEndTime:
            assert isinstance(val, dt.datetime)
            converted = convert("UTCTIMESTAMP", val)
        elif tag is FT.TotalVolumeTraded:
            assert isinstance(val, Decimal)
            converted = convert("QTY", val)
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
    def cast(cls, msg: FixMessage) -> "TradingSessionStatus":
        return _cast(cls, msg)