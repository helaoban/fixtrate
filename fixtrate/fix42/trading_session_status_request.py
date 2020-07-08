import typing as t
import typing_extensions as te
from collections import OrderedDict
import datetime as dt
from decimal import Decimal

from fixtrate.message import FixMessage
from .types import FixTag as FT, TYPE_MAP
from .validate import validate, convert, cast as _cast


class TradingSessionStatusRequest(FixMessage):

    _msg_type = "g"

    _fields = OrderedDict({
        FT.TradSesReqID: True,
        FT.TradingSessionID: False,
        FT.TradSesMethod: False,
        FT.TradSesMode: False,
        FT.SubscriptionRequestType: True,
    })

    def __init__(
        self,
        trad_ses_req_id: str,
        subscription_request_type: str,
    ) -> None:
        super().__init__()
        self.append_pair(35, self._msg_type)
        self.append_pair(
            FT.TradSesReqID,
            convert("STRING", trad_ses_req_id),
        )
        self.append_pair(
            FT.SubscriptionRequestType,
            convert("CHAR", subscription_request_type),
        )

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TradSesReqID]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SubscriptionRequestType]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TradingSessionID]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TradSesMethod]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TradSesMode]) -> t.Optional[int]:
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
        val: str,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.TradingSessionID],
        val: t.Optional[str],
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
        tag: te.Literal[FT.SubscriptionRequestType],
        val: str,
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
        elif tag is FT.SubscriptionRequestType:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        else:
            raise ValueError(f"{tag} is not a valid FIX tag")
        self.append_pair(tag, converted)

    @classmethod
    def cast(cls, msg: FixMessage) -> "TradingSessionStatusRequest":
        return _cast(cls, msg)