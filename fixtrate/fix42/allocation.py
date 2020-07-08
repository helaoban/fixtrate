import typing as t
import typing_extensions as te
from collections import OrderedDict
import datetime as dt
from decimal import Decimal

from fixtrate.message import FixMessage
from .types import FixTag as FT, TYPE_MAP
from .validate import validate, convert, cast as _cast


class Allocation(FixMessage):

    _msg_type = "J"

    _fields = OrderedDict({
        FT.AllocID: True,
        FT.AllocTransType: True,
        FT.RefAllocID: False,
        FT.AllocLinkID: False,
        FT.AllocLinkType: False,
        FT.NoOrders: False,
        FT.ClOrdID: False,
        FT.OrderID: False,
        FT.SecondaryOrderID: False,
        FT.ListID: False,
        FT.WaveNo: False,
        FT.NoExecs: False,
        FT.LastShares: False,
        FT.ExecID: False,
        FT.LastPx: False,
        FT.LastCapacity: False,
        FT.Side: True,
        FT.Symbol: True,
        FT.SymbolSfx: False,
        FT.SecurityID: False,
        FT.IDSource: False,
        FT.SecurityType: False,
        FT.MaturityMonthYear: False,
        FT.MaturityDay: False,
        FT.PutOrCall: False,
        FT.StrikePrice: False,
        FT.OptAttribute: False,
        FT.ContractMultiplier: False,
        FT.CouponRate: False,
        FT.SecurityExchange: False,
        FT.Issuer: False,
        FT.EncodedIssuerLen: False,
        FT.EncodedIssuer: False,
        FT.SecurityDesc: False,
        FT.EncodedSecurityDescLen: False,
        FT.EncodedSecurityDesc: False,
        FT.Shares: True,
        FT.LastMkt: False,
        FT.TradingSessionID: False,
        FT.AvgPx: True,
        FT.Currency: False,
        FT.AvgPrxPrecision: False,
        FT.TradeDate: True,
        FT.TransactTime: False,
        FT.SettlmntTyp: False,
        FT.FutSettDate: False,
        FT.GrossTradeAmt: False,
        FT.NetMoney: False,
        FT.OpenClose: False,
        FT.Text: False,
        FT.EncodedTextLen: False,
        FT.EncodedText: False,
        FT.NumDaysInterest: False,
        FT.AccruedInterestRate: False,
        FT.NoAllocs: False,
        FT.AllocAccount: False,
        FT.AllocPrice: False,
        FT.AllocShares: True,
        FT.ProcessCode: False,
        FT.BrokerOfCredit: False,
        FT.NotifyBrokerOfCredit: False,
        FT.AllocHandlInst: False,
        FT.AllocText: False,
        FT.EncodedAllocTextLen: False,
        FT.EncodedAllocText: False,
        FT.ExecBroker: False,
        FT.ClientID: False,
        FT.Commission: False,
        FT.CommType: False,
        FT.AllocAvgPx: False,
        FT.AllocNetMoney: False,
        FT.SettlCurrAmt: False,
        FT.SettlCurrency: False,
        FT.SettlCurrFxRate: False,
        FT.SettlCurrFxRateCalc: False,
        FT.AccruedInterestAmt: False,
        FT.SettlInstMode: False,
        FT.NoMiscFees: False,
        FT.MiscFeeAmt: False,
        FT.MiscFeeCurr: False,
        FT.MiscFeeType: False,
    })

    def __init__(
        self,
        alloc_id: str,
        alloc_trans_type: str,
        side: str,
        symbol: str,
        shares: Decimal,
        avg_px: Decimal,
        trade_date: dt.date,
        alloc_shares: Decimal,
    ) -> None:
        super().__init__()
        self.append_pair(35, self._msg_type)
        self.append_pair(
            FT.AllocID,
            convert("STRING", alloc_id),
        )
        self.append_pair(
            FT.AllocTransType,
            convert("CHAR", alloc_trans_type),
        )
        self.append_pair(
            FT.Side,
            convert("CHAR", side),
        )
        self.append_pair(
            FT.Symbol,
            convert("STRING", symbol),
        )
        self.append_pair(
            FT.Shares,
            convert("QTY", shares),
        )
        self.append_pair(
            FT.AvgPx,
            convert("PRICE", avg_px),
        )
        self.append_pair(
            FT.TradeDate,
            convert("LOCALMKTDATE", trade_date),
        )
        self.append_pair(
            FT.AllocShares,
            convert("QTY", alloc_shares),
        )

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.AllocID]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.AllocTransType]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.Side]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.Symbol]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.Shares]) -> Decimal:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.AvgPx]) -> Decimal:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TradeDate]) -> dt.date:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.AllocShares]) -> Decimal:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.RefAllocID]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.AllocLinkID]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.AllocLinkType]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.NoOrders]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ClOrdID]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.OrderID]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SecondaryOrderID]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ListID]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.WaveNo]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.NoExecs]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.LastShares]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ExecID]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.LastPx]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.LastCapacity]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SymbolSfx]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SecurityID]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.IDSource]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SecurityType]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.MaturityMonthYear]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.MaturityDay]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.PutOrCall]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.StrikePrice]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.OptAttribute]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ContractMultiplier]) -> t.Optional[float]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.CouponRate]) -> t.Optional[float]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SecurityExchange]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.Issuer]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.EncodedIssuerLen]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.EncodedIssuer]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SecurityDesc]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.EncodedSecurityDescLen]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.EncodedSecurityDesc]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.LastMkt]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TradingSessionID]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.Currency]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.AvgPrxPrecision]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TransactTime]) -> t.Optional[dt.datetime]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SettlmntTyp]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.FutSettDate]) -> t.Optional[dt.date]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.GrossTradeAmt]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.NetMoney]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.OpenClose]) -> t.Optional[str]:
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

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.NumDaysInterest]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.AccruedInterestRate]) -> t.Optional[float]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.NoAllocs]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.AllocAccount]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.AllocPrice]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ProcessCode]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.BrokerOfCredit]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.NotifyBrokerOfCredit]) -> t.Optional[bool]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.AllocHandlInst]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.AllocText]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.EncodedAllocTextLen]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.EncodedAllocText]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ExecBroker]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ClientID]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.Commission]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.CommType]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.AllocAvgPx]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.AllocNetMoney]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SettlCurrAmt]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SettlCurrency]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SettlCurrFxRate]) -> t.Optional[float]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SettlCurrFxRateCalc]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.AccruedInterestAmt]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SettlInstMode]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.NoMiscFees]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.MiscFeeAmt]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.MiscFeeCurr]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.MiscFeeType]) -> t.Optional[str]:
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
        tag: te.Literal[FT.AllocID],
        val: str,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.AllocTransType],
        val: str,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.RefAllocID],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.AllocLinkID],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.AllocLinkType],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.NoOrders],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.ClOrdID],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.OrderID],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SecondaryOrderID],
        val: t.Optional[str],
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
        tag: te.Literal[FT.WaveNo],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.NoExecs],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.LastShares],
        val: t.Optional[Decimal],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.ExecID],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.LastPx],
        val: t.Optional[Decimal],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.LastCapacity],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.Side],
        val: str,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.Symbol],
        val: str,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SymbolSfx],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SecurityID],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.IDSource],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SecurityType],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.MaturityMonthYear],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.MaturityDay],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.PutOrCall],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.StrikePrice],
        val: t.Optional[Decimal],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.OptAttribute],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.ContractMultiplier],
        val: t.Optional[float],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.CouponRate],
        val: t.Optional[float],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SecurityExchange],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.Issuer],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.EncodedIssuerLen],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.EncodedIssuer],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SecurityDesc],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.EncodedSecurityDescLen],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.EncodedSecurityDesc],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.Shares],
        val: Decimal,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.LastMkt],
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
        tag: te.Literal[FT.AvgPx],
        val: Decimal,
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
        tag: te.Literal[FT.AvgPrxPrecision],
        val: t.Optional[int],
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
        tag: te.Literal[FT.GrossTradeAmt],
        val: t.Optional[Decimal],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.NetMoney],
        val: t.Optional[Decimal],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.OpenClose],
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

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.NumDaysInterest],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.AccruedInterestRate],
        val: t.Optional[float],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.NoAllocs],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.AllocAccount],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.AllocPrice],
        val: t.Optional[Decimal],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.AllocShares],
        val: Decimal,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.ProcessCode],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.BrokerOfCredit],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.NotifyBrokerOfCredit],
        val: t.Optional[bool],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.AllocHandlInst],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.AllocText],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.EncodedAllocTextLen],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.EncodedAllocText],
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
        tag: te.Literal[FT.ClientID],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.Commission],
        val: t.Optional[Decimal],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.CommType],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.AllocAvgPx],
        val: t.Optional[Decimal],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.AllocNetMoney],
        val: t.Optional[Decimal],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SettlCurrAmt],
        val: t.Optional[Decimal],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SettlCurrency],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SettlCurrFxRate],
        val: t.Optional[float],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SettlCurrFxRateCalc],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.AccruedInterestAmt],
        val: t.Optional[Decimal],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SettlInstMode],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.NoMiscFees],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.MiscFeeAmt],
        val: t.Optional[Decimal],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.MiscFeeCurr],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.MiscFeeType],
        val: t.Optional[str],
    ) -> None:
        ...

    def append(self, tag: FT, val: t.Any):  # NOQA
        if tag is FT.AllocID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.AllocTransType:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.RefAllocID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.AllocLinkID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.AllocLinkType:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.NoOrders:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.ClOrdID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.OrderID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.SecondaryOrderID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.ListID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.WaveNo:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.NoExecs:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.LastShares:
            assert isinstance(val, Decimal)
            converted = convert("QTY", val)
        elif tag is FT.ExecID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.LastPx:
            assert isinstance(val, Decimal)
            converted = convert("PRICE", val)
        elif tag is FT.LastCapacity:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.Side:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.Symbol:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.SymbolSfx:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.SecurityID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.IDSource:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.SecurityType:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.MaturityMonthYear:
            assert isinstance(val, str)
            converted = convert("MONTHYEAR", val)
        elif tag is FT.MaturityDay:
            assert isinstance(val, int)
            converted = convert("DAYOFMONTH", val)
        elif tag is FT.PutOrCall:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.StrikePrice:
            assert isinstance(val, Decimal)
            converted = convert("PRICE", val)
        elif tag is FT.OptAttribute:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.ContractMultiplier:
            assert isinstance(val, float)
            converted = convert("FLOAT", val)
        elif tag is FT.CouponRate:
            assert isinstance(val, float)
            converted = convert("FLOAT", val)
        elif tag is FT.SecurityExchange:
            assert isinstance(val, str)
            converted = convert("EXCHANGE", val)
        elif tag is FT.Issuer:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.EncodedIssuerLen:
            assert isinstance(val, int)
            converted = convert("LENGTH", val)
        elif tag is FT.EncodedIssuer:
            assert isinstance(val, str)
            converted = convert("DATA", val)
        elif tag is FT.SecurityDesc:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.EncodedSecurityDescLen:
            assert isinstance(val, int)
            converted = convert("LENGTH", val)
        elif tag is FT.EncodedSecurityDesc:
            assert isinstance(val, str)
            converted = convert("DATA", val)
        elif tag is FT.Shares:
            assert isinstance(val, Decimal)
            converted = convert("QTY", val)
        elif tag is FT.LastMkt:
            assert isinstance(val, str)
            converted = convert("EXCHANGE", val)
        elif tag is FT.TradingSessionID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.AvgPx:
            assert isinstance(val, Decimal)
            converted = convert("PRICE", val)
        elif tag is FT.Currency:
            assert isinstance(val, str)
            converted = convert("CURRENCY", val)
        elif tag is FT.AvgPrxPrecision:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.TradeDate:
            assert isinstance(val, dt.date)
            converted = convert("LOCALMKTDATE", val)
        elif tag is FT.TransactTime:
            assert isinstance(val, dt.datetime)
            converted = convert("UTCTIMESTAMP", val)
        elif tag is FT.SettlmntTyp:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.FutSettDate:
            assert isinstance(val, dt.date)
            converted = convert("LOCALMKTDATE", val)
        elif tag is FT.GrossTradeAmt:
            assert isinstance(val, Decimal)
            converted = convert("AMT", val)
        elif tag is FT.NetMoney:
            assert isinstance(val, Decimal)
            converted = convert("AMT", val)
        elif tag is FT.OpenClose:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.Text:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.EncodedTextLen:
            assert isinstance(val, int)
            converted = convert("LENGTH", val)
        elif tag is FT.EncodedText:
            assert isinstance(val, str)
            converted = convert("DATA", val)
        elif tag is FT.NumDaysInterest:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.AccruedInterestRate:
            assert isinstance(val, float)
            converted = convert("FLOAT", val)
        elif tag is FT.NoAllocs:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.AllocAccount:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.AllocPrice:
            assert isinstance(val, Decimal)
            converted = convert("PRICE", val)
        elif tag is FT.AllocShares:
            assert isinstance(val, Decimal)
            converted = convert("QTY", val)
        elif tag is FT.ProcessCode:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.BrokerOfCredit:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.NotifyBrokerOfCredit:
            assert isinstance(val, bool)
            converted = convert("BOOLEAN", val)
        elif tag is FT.AllocHandlInst:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.AllocText:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.EncodedAllocTextLen:
            assert isinstance(val, int)
            converted = convert("LENGTH", val)
        elif tag is FT.EncodedAllocText:
            assert isinstance(val, str)
            converted = convert("DATA", val)
        elif tag is FT.ExecBroker:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.ClientID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.Commission:
            assert isinstance(val, Decimal)
            converted = convert("AMT", val)
        elif tag is FT.CommType:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.AllocAvgPx:
            assert isinstance(val, Decimal)
            converted = convert("PRICE", val)
        elif tag is FT.AllocNetMoney:
            assert isinstance(val, Decimal)
            converted = convert("AMT", val)
        elif tag is FT.SettlCurrAmt:
            assert isinstance(val, Decimal)
            converted = convert("AMT", val)
        elif tag is FT.SettlCurrency:
            assert isinstance(val, str)
            converted = convert("CURRENCY", val)
        elif tag is FT.SettlCurrFxRate:
            assert isinstance(val, float)
            converted = convert("FLOAT", val)
        elif tag is FT.SettlCurrFxRateCalc:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.AccruedInterestAmt:
            assert isinstance(val, Decimal)
            converted = convert("AMT", val)
        elif tag is FT.SettlInstMode:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.NoMiscFees:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.MiscFeeAmt:
            assert isinstance(val, Decimal)
            converted = convert("AMT", val)
        elif tag is FT.MiscFeeCurr:
            assert isinstance(val, str)
            converted = convert("CURRENCY", val)
        elif tag is FT.MiscFeeType:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        else:
            raise ValueError(f"{tag} is not a valid FIX tag")
        self.append_pair(tag, converted)

    @classmethod
    def cast(cls, msg: FixMessage) -> "Allocation":
        return _cast(cls, msg)