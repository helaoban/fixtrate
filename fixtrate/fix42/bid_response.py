import typing as t
import typing_extensions as te
from collections import OrderedDict
import datetime as dt
from decimal import Decimal

from fixtrate.message import FixMessage
from .types import FixTag as FT, TYPE_MAP
from .validate import validate, convert, cast as _cast


class BidResponse(FixMessage):

    _msg_type = "l"

    _fields = OrderedDict({
        FT.BidID: False,
        FT.ClientBidID: False,
        FT.NoBidComponents: True,
        FT.Commission: True,
        FT.CommType: True,
        FT.ListID: False,
        FT.Country: False,
        FT.Side: False,
        FT.Price: False,
        FT.PriceType: False,
        FT.FairValue: False,
        FT.NetGrossInd: False,
        FT.SettlmntTyp: False,
        FT.FutSettDate: False,
        FT.TradingSessionID: False,
        FT.Text: False,
        FT.EncodedTextLen: False,
        FT.EncodedText: False,
    })

    def __init__(
        self,
        no_bid_components: int,
        commission: Decimal,
        comm_type: str,
    ) -> None:
        super().__init__()
        self.append_pair(35, self._msg_type)
        self.append_pair(
            FT.NoBidComponents,
            convert("INT", no_bid_components),
        )
        self.append_pair(
            FT.Commission,
            convert("AMT", commission),
        )
        self.append_pair(
            FT.CommType,
            convert("CHAR", comm_type),
        )

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.NoBidComponents]) -> int:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.Commission]) -> Decimal:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.CommType]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.BidID]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ClientBidID]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ListID]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.Country]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.Side]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.Price]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.PriceType]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.FairValue]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.NetGrossInd]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SettlmntTyp]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.FutSettDate]) -> t.Optional[dt.date]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TradingSessionID]) -> t.Optional[str]:
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
        tag: te.Literal[FT.BidID],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.ClientBidID],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.NoBidComponents],
        val: int,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.Commission],
        val: Decimal,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.CommType],
        val: str,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.ListID],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.Country],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.Side],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.Price],
        val: t.Optional[Decimal],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.PriceType],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.FairValue],
        val: t.Optional[Decimal],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.NetGrossInd],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SettlmntTyp],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.FutSettDate],
        val: t.Optional[dt.date],
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
        if tag is FT.BidID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.ClientBidID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.NoBidComponents:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.Commission:
            assert isinstance(val, Decimal)
            converted = convert("AMT", val)
        elif tag is FT.CommType:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.ListID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.Country:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.Side:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.Price:
            assert isinstance(val, Decimal)
            converted = convert("PRICE", val)
        elif tag is FT.PriceType:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.FairValue:
            assert isinstance(val, Decimal)
            converted = convert("AMT", val)
        elif tag is FT.NetGrossInd:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.SettlmntTyp:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.FutSettDate:
            assert isinstance(val, dt.date)
            converted = convert("LOCALMKTDATE", val)
        elif tag is FT.TradingSessionID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
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
    def cast(cls, msg: FixMessage) -> "BidResponse":
        return _cast(cls, msg)