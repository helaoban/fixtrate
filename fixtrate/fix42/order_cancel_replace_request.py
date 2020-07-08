import typing as t
import typing_extensions as te
from collections import OrderedDict
import datetime as dt
from decimal import Decimal

from fixtrate.message import FixMessage
from .types import FixTag as FT, TYPE_MAP
from .validate import validate, convert, cast as _cast


class OrderCancelReplaceRequest(FixMessage):

    _msg_type = "G"

    _fields = OrderedDict({
        FT.OrderID: False,
        FT.ClientID: False,
        FT.ExecBroker: False,
        FT.OrigClOrdID: True,
        FT.ClOrdID: True,
        FT.ListID: False,
        FT.Account: False,
        FT.NoAllocs: False,
        FT.AllocAccount: False,
        FT.AllocShares: False,
        FT.SettlmntTyp: False,
        FT.FutSettDate: False,
        FT.HandlInst: True,
        FT.ExecInst: False,
        FT.MinQty: False,
        FT.MaxFloor: False,
        FT.ExDestination: False,
        FT.NoTradingSessions: False,
        FT.TradingSessionID: False,
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
        FT.Side: True,
        FT.TransactTime: True,
        FT.OrderQty: False,
        FT.CashOrderQty: False,
        FT.OrdType: True,
        FT.Price: False,
        FT.StopPx: False,
        FT.PegDifference: False,
        FT.DiscretionInst: False,
        FT.DiscretionOffset: False,
        FT.ComplianceID: False,
        FT.SolicitedFlag: False,
        FT.Currency: False,
        FT.TimeInForce: False,
        FT.EffectiveTime: False,
        FT.ExpireDate: False,
        FT.ExpireTime: False,
        FT.GTBookingInst: False,
        FT.Commission: False,
        FT.CommType: False,
        FT.Rule80A: False,
        FT.ForexReq: False,
        FT.SettlCurrency: False,
        FT.Text: False,
        FT.EncodedTextLen: False,
        FT.EncodedText: False,
        FT.FutSettDate2: False,
        FT.OrderQty2: False,
        FT.OpenClose: False,
        FT.CoveredOrUncovered: False,
        FT.CustomerOrFirm: False,
        FT.MaxShow: False,
        FT.LocateReqd: False,
        FT.ClearingFirm: False,
        FT.ClearingAccount: False,
    })

    def __init__(
        self,
        orig_cl_ord_id: str,
        cl_ord_id: str,
        handl_inst: str,
        symbol: str,
        side: str,
        transact_time: dt.datetime,
        ord_type: str,
    ) -> None:
        super().__init__()
        self.append_pair(35, self._msg_type)
        self.append_pair(
            FT.OrigClOrdID,
            convert("STRING", orig_cl_ord_id),
        )
        self.append_pair(
            FT.ClOrdID,
            convert("STRING", cl_ord_id),
        )
        self.append_pair(
            FT.HandlInst,
            convert("CHAR", handl_inst),
        )
        self.append_pair(
            FT.Symbol,
            convert("STRING", symbol),
        )
        self.append_pair(
            FT.Side,
            convert("CHAR", side),
        )
        self.append_pair(
            FT.TransactTime,
            convert("UTCTIMESTAMP", transact_time),
        )
        self.append_pair(
            FT.OrdType,
            convert("CHAR", ord_type),
        )

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.OrigClOrdID]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ClOrdID]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.HandlInst]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.Symbol]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.Side]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TransactTime]) -> dt.datetime:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.OrdType]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.OrderID]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ClientID]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ExecBroker]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ListID]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.Account]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.NoAllocs]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.AllocAccount]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.AllocShares]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SettlmntTyp]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.FutSettDate]) -> t.Optional[dt.date]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ExecInst]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.MinQty]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.MaxFloor]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ExDestination]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.NoTradingSessions]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TradingSessionID]) -> t.Optional[str]:
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
    def get(self, tag: te.Literal[FT.OrderQty]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.CashOrderQty]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.Price]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.StopPx]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.PegDifference]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.DiscretionInst]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.DiscretionOffset]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ComplianceID]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SolicitedFlag]) -> t.Optional[bool]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.Currency]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TimeInForce]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.EffectiveTime]) -> t.Optional[dt.datetime]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ExpireDate]) -> t.Optional[dt.date]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ExpireTime]) -> t.Optional[dt.datetime]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.GTBookingInst]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.Commission]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.CommType]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.Rule80A]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ForexReq]) -> t.Optional[bool]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SettlCurrency]) -> t.Optional[str]:
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
    def get(self, tag: te.Literal[FT.FutSettDate2]) -> t.Optional[dt.date]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.OrderQty2]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.OpenClose]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.CoveredOrUncovered]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.CustomerOrFirm]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.MaxShow]) -> t.Optional[Decimal]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.LocateReqd]) -> t.Optional[bool]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ClearingFirm]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ClearingAccount]) -> t.Optional[str]:
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
        tag: te.Literal[FT.OrderID],
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
        tag: te.Literal[FT.ExecBroker],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.OrigClOrdID],
        val: str,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.ClOrdID],
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
        tag: te.Literal[FT.Account],
        val: t.Optional[str],
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
        tag: te.Literal[FT.AllocShares],
        val: t.Optional[Decimal],
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
        tag: te.Literal[FT.HandlInst],
        val: str,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.ExecInst],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.MinQty],
        val: t.Optional[Decimal],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.MaxFloor],
        val: t.Optional[Decimal],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.ExDestination],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.NoTradingSessions],
        val: t.Optional[int],
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
        tag: te.Literal[FT.Side],
        val: str,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.TransactTime],
        val: dt.datetime,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.OrderQty],
        val: t.Optional[Decimal],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.CashOrderQty],
        val: t.Optional[Decimal],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.OrdType],
        val: str,
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
        tag: te.Literal[FT.StopPx],
        val: t.Optional[Decimal],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.PegDifference],
        val: t.Optional[Decimal],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.DiscretionInst],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.DiscretionOffset],
        val: t.Optional[Decimal],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.ComplianceID],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SolicitedFlag],
        val: t.Optional[bool],
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
        tag: te.Literal[FT.TimeInForce],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.EffectiveTime],
        val: t.Optional[dt.datetime],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.ExpireDate],
        val: t.Optional[dt.date],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.ExpireTime],
        val: t.Optional[dt.datetime],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.GTBookingInst],
        val: t.Optional[int],
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
        tag: te.Literal[FT.Rule80A],
        val: t.Optional[str],
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
        tag: te.Literal[FT.SettlCurrency],
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
        tag: te.Literal[FT.FutSettDate2],
        val: t.Optional[dt.date],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.OrderQty2],
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
        tag: te.Literal[FT.CoveredOrUncovered],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.CustomerOrFirm],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.MaxShow],
        val: t.Optional[Decimal],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.LocateReqd],
        val: t.Optional[bool],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.ClearingFirm],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.ClearingAccount],
        val: t.Optional[str],
    ) -> None:
        ...

    def append(self, tag: FT, val: t.Any):  # NOQA
        if tag is FT.OrderID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.ClientID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.ExecBroker:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.OrigClOrdID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.ClOrdID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.ListID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.Account:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.NoAllocs:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.AllocAccount:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.AllocShares:
            assert isinstance(val, Decimal)
            converted = convert("QTY", val)
        elif tag is FT.SettlmntTyp:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.FutSettDate:
            assert isinstance(val, dt.date)
            converted = convert("LOCALMKTDATE", val)
        elif tag is FT.HandlInst:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.ExecInst:
            assert isinstance(val, str)
            converted = convert("MULTIPLEVALUESTRING", val)
        elif tag is FT.MinQty:
            assert isinstance(val, Decimal)
            converted = convert("QTY", val)
        elif tag is FT.MaxFloor:
            assert isinstance(val, Decimal)
            converted = convert("QTY", val)
        elif tag is FT.ExDestination:
            assert isinstance(val, str)
            converted = convert("EXCHANGE", val)
        elif tag is FT.NoTradingSessions:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.TradingSessionID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
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
        elif tag is FT.Side:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.TransactTime:
            assert isinstance(val, dt.datetime)
            converted = convert("UTCTIMESTAMP", val)
        elif tag is FT.OrderQty:
            assert isinstance(val, Decimal)
            converted = convert("QTY", val)
        elif tag is FT.CashOrderQty:
            assert isinstance(val, Decimal)
            converted = convert("QTY", val)
        elif tag is FT.OrdType:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.Price:
            assert isinstance(val, Decimal)
            converted = convert("PRICE", val)
        elif tag is FT.StopPx:
            assert isinstance(val, Decimal)
            converted = convert("PRICE", val)
        elif tag is FT.PegDifference:
            assert isinstance(val, Decimal)
            converted = convert("PRICEOFFSET", val)
        elif tag is FT.DiscretionInst:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.DiscretionOffset:
            assert isinstance(val, Decimal)
            converted = convert("PRICEOFFSET", val)
        elif tag is FT.ComplianceID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.SolicitedFlag:
            assert isinstance(val, bool)
            converted = convert("BOOLEAN", val)
        elif tag is FT.Currency:
            assert isinstance(val, str)
            converted = convert("CURRENCY", val)
        elif tag is FT.TimeInForce:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.EffectiveTime:
            assert isinstance(val, dt.datetime)
            converted = convert("UTCTIMESTAMP", val)
        elif tag is FT.ExpireDate:
            assert isinstance(val, dt.date)
            converted = convert("LOCALMKTDATE", val)
        elif tag is FT.ExpireTime:
            assert isinstance(val, dt.datetime)
            converted = convert("UTCTIMESTAMP", val)
        elif tag is FT.GTBookingInst:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.Commission:
            assert isinstance(val, Decimal)
            converted = convert("AMT", val)
        elif tag is FT.CommType:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.Rule80A:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.ForexReq:
            assert isinstance(val, bool)
            converted = convert("BOOLEAN", val)
        elif tag is FT.SettlCurrency:
            assert isinstance(val, str)
            converted = convert("CURRENCY", val)
        elif tag is FT.Text:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.EncodedTextLen:
            assert isinstance(val, int)
            converted = convert("LENGTH", val)
        elif tag is FT.EncodedText:
            assert isinstance(val, str)
            converted = convert("DATA", val)
        elif tag is FT.FutSettDate2:
            assert isinstance(val, dt.date)
            converted = convert("LOCALMKTDATE", val)
        elif tag is FT.OrderQty2:
            assert isinstance(val, Decimal)
            converted = convert("QTY", val)
        elif tag is FT.OpenClose:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.CoveredOrUncovered:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.CustomerOrFirm:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.MaxShow:
            assert isinstance(val, Decimal)
            converted = convert("QTY", val)
        elif tag is FT.LocateReqd:
            assert isinstance(val, bool)
            converted = convert("BOOLEAN", val)
        elif tag is FT.ClearingFirm:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.ClearingAccount:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        else:
            raise ValueError(f"{tag} is not a valid FIX tag")
        self.append_pair(tag, converted)

    @classmethod
    def cast(cls, msg: FixMessage) -> "OrderCancelReplaceRequest":
        return _cast(cls, msg)
