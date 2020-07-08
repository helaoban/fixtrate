import typing as t
import typing_extensions as te
from collections import OrderedDict
import datetime as dt
from decimal import Decimal

from fixtrate.message import FixMessage
from .types import FixTag as FT, TYPE_MAP
from .validate import validate, convert, cast as _cast


class BidRequest(FixMessage):

    _msg_type = "k"

    _fields = OrderedDict({
        FT.BidID: False,
        FT.ClientBidID: True,
        FT.BidRequestTransType: True,
        FT.ListName: False,
        FT.TotalNumSecurities: True,
        FT.BidType: True,
        FT.NumTickets: False,
        FT.Currency: False,
        FT.SideValue1: False,
        FT.SideValue2: False,
        FT.NoBidDescriptors: False,
        FT.BidDescriptorType: False,
        FT.BidDescriptor: False,
        FT.SideValueInd: False,
        FT.LiquidityValue: False,
        FT.LiquidityNumSecurities: False,
        FT.LiquidityPctLow: False,
        FT.LiquidityPctHigh: False,
        FT.EFPTrackingError: False,
        FT.FairValue: False,
        FT.OutsideIndexPct: False,
        FT.ValueOfFutures: False,
        FT.NoBidComponents: False,
        FT.ListID: False,
        FT.Side: False,
        FT.TradingSessionID: False,
        FT.NetGrossInd: False,
        FT.SettlmntTyp: False,
        FT.FutSettDate: False,
        FT.Account: False,
        FT.LiquidityIndType: False,
        FT.WtAverageLiquidity: False,
        FT.ExchangeForPhysical: False,
        FT.OutMainCntryUIndex: False,
        FT.CrossPercent: False,
        FT.ProgRptReqs: False,
        FT.ProgPeriodInterval: False,
        FT.IncTaxInd: False,
        FT.ForexReq: False,
        FT.NumBidders: False,
        FT.TradeDate: False,
        FT.TradeType: True,
        FT.BasisPxType: True,
        FT.StrikeTime: False,
        FT.Text: False,
        FT.EncodedTextLen: False,
        FT.EncodedText: False,
    })

    def __init__(
        self,
        client_bid_id: str,
        bid_request_trans_type: str,
        total_num_securities: int,
        bid_type: int,
        trade_type: str,
        basis_px_type: str,
    ) -> None:
        super().__init__()
        self.append_pair(35, self._msg_type)
        self.append_pair(
            FT.ClientBidID,
            convert("STRING", client_bid_id),
        )
        self.append_pair(
            FT.BidRequestTransType,
            convert("CHAR", bid_request_trans_type),
        )
        self.append_pair(
            FT.TotalNumSecurities,
            convert("INT", total_num_securities),
        )
        self.append_pair(
            FT.BidType,
            convert("INT", bid_type),
        )
        self.append_pair(
            FT.TradeType,
            convert("CHAR", trade_type),
        )
        self.append_pair(
            FT.BasisPxType,
            convert("CHAR", basis_px_type),
        )

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ClientBidID]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.BidRequestTransType]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TotalNumSecurities]) -> int:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.BidType]) -> int:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TradeType]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.BasisPxType]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.BidID]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ListName]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.NumTickets]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.Currency]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SideValue1]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SideValue2]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.NoBidDescriptors]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.BidDescriptorType]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.BidDescriptor]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SideValueInd]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.LiquidityValue]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.LiquidityNumSecurities]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.LiquidityPctLow]) -> t.Optional[float]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.LiquidityPctHigh]) -> t.Optional[float]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.EFPTrackingError]) -> t.Optional[float]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.FairValue]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.OutsideIndexPct]) -> t.Optional[float]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ValueOfFutures]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.NoBidComponents]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ListID]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.Side]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TradingSessionID]) -> t.Optional[str]:
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
    def get(self, tag: te.Literal[FT.Account]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.LiquidityIndType]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.WtAverageLiquidity]) -> t.Optional[float]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ExchangeForPhysical]) -> t.Optional[bool]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.OutMainCntryUIndex]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.CrossPercent]) -> t.Optional[float]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ProgRptReqs]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ProgPeriodInterval]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.IncTaxInd]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ForexReq]) -> t.Optional[bool]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.NumBidders]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TradeDate]) -> t.Optional[dt.date]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.StrikeTime]) -> t.Optional[dt.datetime]:
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
        val: str,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.BidRequestTransType],
        val: str,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.ListName],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.TotalNumSecurities],
        val: int,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.BidType],
        val: int,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.NumTickets],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.Currency],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SideValue1],
        val: t.Optional[Decimal],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SideValue2],
        val: t.Optional[Decimal],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.NoBidDescriptors],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.BidDescriptorType],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.BidDescriptor],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SideValueInd],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.LiquidityValue],
        val: t.Optional[Decimal],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.LiquidityNumSecurities],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.LiquidityPctLow],
        val: t.Optional[float],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.LiquidityPctHigh],
        val: t.Optional[float],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.EFPTrackingError],
        val: t.Optional[float],
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
        tag: te.Literal[FT.OutsideIndexPct],
        val: t.Optional[float],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.ValueOfFutures],
        val: t.Optional[Decimal],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.NoBidComponents],
        val: t.Optional[int],
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
        tag: te.Literal[FT.Side],
        val: t.Optional[str],
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
        tag: te.Literal[FT.Account],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.LiquidityIndType],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.WtAverageLiquidity],
        val: t.Optional[float],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.ExchangeForPhysical],
        val: t.Optional[bool],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.OutMainCntryUIndex],
        val: t.Optional[Decimal],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.CrossPercent],
        val: t.Optional[float],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.ProgRptReqs],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.ProgPeriodInterval],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.IncTaxInd],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.ForexReq],
        val: t.Optional[bool],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.NumBidders],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.TradeDate],
        val: t.Optional[dt.date],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.TradeType],
        val: str,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.BasisPxType],
        val: str,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.StrikeTime],
        val: t.Optional[dt.datetime],
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
        elif tag is FT.BidRequestTransType:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.ListName:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.TotalNumSecurities:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.BidType:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.NumTickets:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.Currency:
            assert isinstance(val, str)
            converted = convert("CURRENCY", val)
        elif tag is FT.SideValue1:
            assert isinstance(val, Decimal)
            converted = convert("AMT", val)
        elif tag is FT.SideValue2:
            assert isinstance(val, Decimal)
            converted = convert("AMT", val)
        elif tag is FT.NoBidDescriptors:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.BidDescriptorType:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.BidDescriptor:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.SideValueInd:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.LiquidityValue:
            assert isinstance(val, Decimal)
            converted = convert("AMT", val)
        elif tag is FT.LiquidityNumSecurities:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.LiquidityPctLow:
            assert isinstance(val, float)
            converted = convert("FLOAT", val)
        elif tag is FT.LiquidityPctHigh:
            assert isinstance(val, float)
            converted = convert("FLOAT", val)
        elif tag is FT.EFPTrackingError:
            assert isinstance(val, float)
            converted = convert("FLOAT", val)
        elif tag is FT.FairValue:
            assert isinstance(val, Decimal)
            converted = convert("AMT", val)
        elif tag is FT.OutsideIndexPct:
            assert isinstance(val, float)
            converted = convert("FLOAT", val)
        elif tag is FT.ValueOfFutures:
            assert isinstance(val, Decimal)
            converted = convert("AMT", val)
        elif tag is FT.NoBidComponents:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.ListID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.Side:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.TradingSessionID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.NetGrossInd:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.SettlmntTyp:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.FutSettDate:
            assert isinstance(val, dt.date)
            converted = convert("LOCALMKTDATE", val)
        elif tag is FT.Account:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.LiquidityIndType:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.WtAverageLiquidity:
            assert isinstance(val, float)
            converted = convert("FLOAT", val)
        elif tag is FT.ExchangeForPhysical:
            assert isinstance(val, bool)
            converted = convert("BOOLEAN", val)
        elif tag is FT.OutMainCntryUIndex:
            assert isinstance(val, Decimal)
            converted = convert("AMT", val)
        elif tag is FT.CrossPercent:
            assert isinstance(val, float)
            converted = convert("FLOAT", val)
        elif tag is FT.ProgRptReqs:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.ProgPeriodInterval:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.IncTaxInd:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.ForexReq:
            assert isinstance(val, bool)
            converted = convert("BOOLEAN", val)
        elif tag is FT.NumBidders:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.TradeDate:
            assert isinstance(val, dt.date)
            converted = convert("LOCALMKTDATE", val)
        elif tag is FT.TradeType:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.BasisPxType:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.StrikeTime:
            assert isinstance(val, dt.datetime)
            converted = convert("UTCTIMESTAMP", val)
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
    def cast(cls, msg: FixMessage) -> "BidRequest":
        return _cast(cls, msg)