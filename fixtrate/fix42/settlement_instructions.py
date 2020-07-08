import typing as t
import typing_extensions as te
from collections import OrderedDict
import datetime as dt
from decimal import Decimal

from fix.message import FixMessage
from .types import FixTag as FT, TYPE_MAP
from .validate import validate, convert, cast as _cast


class SettlementInstructions(FixMessage):

    _msg_type = "T"

    _fields = OrderedDict({
        FT.SettlInstID: True,
        FT.SettlInstTransType: True,
        FT.SettlInstRefID: True,
        FT.SettlInstMode: True,
        FT.SettlInstSource: True,
        FT.AllocAccount: True,
        FT.SettlLocation: False,
        FT.TradeDate: False,
        FT.AllocID: False,
        FT.LastMkt: False,
        FT.TradingSessionID: False,
        FT.Side: False,
        FT.SecurityType: False,
        FT.EffectiveTime: False,
        FT.TransactTime: True,
        FT.ClientID: False,
        FT.ExecBroker: False,
        FT.StandInstDbType: False,
        FT.StandInstDbName: False,
        FT.StandInstDbID: False,
        FT.SettlDeliveryType: False,
        FT.SettlDepositoryCode: False,
        FT.SettlBrkrCode: False,
        FT.SettlInstCode: False,
        FT.SecuritySettlAgentName: False,
        FT.SecuritySettlAgentCode: False,
        FT.SecuritySettlAgentAcctNum: False,
        FT.SecuritySettlAgentAcctName: False,
        FT.SecuritySettlAgentContactName: False,
        FT.SecuritySettlAgentContactPhone: False,
        FT.CashSettlAgentName: False,
        FT.CashSettlAgentCode: False,
        FT.CashSettlAgentAcctNum: False,
        FT.CashSettlAgentAcctName: False,
        FT.CashSettlAgentContactName: False,
        FT.CashSettlAgentContactPhone: False,
    })

    def __init__(
        self,
        settl_inst_id: str,
        settl_inst_trans_type: str,
        settl_inst_ref_id: str,
        settl_inst_mode: str,
        settl_inst_source: str,
        alloc_account: str,
        transact_time: dt.datetime,
    ) -> None:
        super().__init__()
        self.append_pair(35, self._msg_type)
        self.append_pair(
            FT.SettlInstID,
            convert("STRING", settl_inst_id),
        )
        self.append_pair(
            FT.SettlInstTransType,
            convert("CHAR", settl_inst_trans_type),
        )
        self.append_pair(
            FT.SettlInstRefID,
            convert("STRING", settl_inst_ref_id),
        )
        self.append_pair(
            FT.SettlInstMode,
            convert("CHAR", settl_inst_mode),
        )
        self.append_pair(
            FT.SettlInstSource,
            convert("CHAR", settl_inst_source),
        )
        self.append_pair(
            FT.AllocAccount,
            convert("STRING", alloc_account),
        )
        self.append_pair(
            FT.TransactTime,
            convert("UTCTIMESTAMP", transact_time),
        )

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SettlInstID]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SettlInstTransType]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SettlInstRefID]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SettlInstMode]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SettlInstSource]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.AllocAccount]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TransactTime]) -> dt.datetime:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SettlLocation]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TradeDate]) -> t.Optional[dt.date]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.AllocID]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.LastMkt]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TradingSessionID]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.Side]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SecurityType]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.EffectiveTime]) -> t.Optional[dt.datetime]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ClientID]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ExecBroker]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.StandInstDbType]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.StandInstDbName]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.StandInstDbID]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SettlDeliveryType]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SettlDepositoryCode]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SettlBrkrCode]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SettlInstCode]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SecuritySettlAgentName]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SecuritySettlAgentCode]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SecuritySettlAgentAcctNum]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SecuritySettlAgentAcctName]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SecuritySettlAgentContactName]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SecuritySettlAgentContactPhone]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.CashSettlAgentName]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.CashSettlAgentCode]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.CashSettlAgentAcctNum]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.CashSettlAgentAcctName]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.CashSettlAgentContactName]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.CashSettlAgentContactPhone]) -> t.Optional[str]:
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
        tag: te.Literal[FT.SettlInstID],
        val: str,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SettlInstTransType],
        val: str,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SettlInstRefID],
        val: str,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SettlInstMode],
        val: str,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SettlInstSource],
        val: str,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.AllocAccount],
        val: str,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SettlLocation],
        val: t.Optional[str],
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
        tag: te.Literal[FT.AllocID],
        val: t.Optional[str],
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
        tag: te.Literal[FT.Side],
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
        tag: te.Literal[FT.EffectiveTime],
        val: t.Optional[dt.datetime],
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
        tag: te.Literal[FT.StandInstDbType],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.StandInstDbName],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.StandInstDbID],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SettlDeliveryType],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SettlDepositoryCode],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SettlBrkrCode],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SettlInstCode],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SecuritySettlAgentName],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SecuritySettlAgentCode],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SecuritySettlAgentAcctNum],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SecuritySettlAgentAcctName],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SecuritySettlAgentContactName],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.SecuritySettlAgentContactPhone],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.CashSettlAgentName],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.CashSettlAgentCode],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.CashSettlAgentAcctNum],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.CashSettlAgentAcctName],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.CashSettlAgentContactName],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.CashSettlAgentContactPhone],
        val: t.Optional[str],
    ) -> None:
        ...

    def append(self, tag: FT, val: t.Any):  # NOQA
        if tag is FT.SettlInstID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.SettlInstTransType:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.SettlInstRefID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.SettlInstMode:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.SettlInstSource:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.AllocAccount:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.SettlLocation:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.TradeDate:
            assert isinstance(val, dt.date)
            converted = convert("LOCALMKTDATE", val)
        elif tag is FT.AllocID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.LastMkt:
            assert isinstance(val, str)
            converted = convert("EXCHANGE", val)
        elif tag is FT.TradingSessionID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.Side:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.SecurityType:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.EffectiveTime:
            assert isinstance(val, dt.datetime)
            converted = convert("UTCTIMESTAMP", val)
        elif tag is FT.TransactTime:
            assert isinstance(val, dt.datetime)
            converted = convert("UTCTIMESTAMP", val)
        elif tag is FT.ClientID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.ExecBroker:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.StandInstDbType:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.StandInstDbName:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.StandInstDbID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.SettlDeliveryType:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.SettlDepositoryCode:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.SettlBrkrCode:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.SettlInstCode:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.SecuritySettlAgentName:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.SecuritySettlAgentCode:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.SecuritySettlAgentAcctNum:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.SecuritySettlAgentAcctName:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.SecuritySettlAgentContactName:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.SecuritySettlAgentContactPhone:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.CashSettlAgentName:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.CashSettlAgentCode:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.CashSettlAgentAcctNum:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.CashSettlAgentAcctName:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.CashSettlAgentContactName:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.CashSettlAgentContactPhone:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        else:
            raise ValueError(f"{tag} is not a valid FIX tag")
        self.append_pair(tag, converted)

    @classmethod
    def cast(cls, msg: FixMessage) -> "SettlementInstructions":
        return _cast(cls, msg)