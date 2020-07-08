import typing as t
import typing_extensions as te
from collections import OrderedDict
import datetime as dt
from decimal import Decimal

from fixtrate.message import FixMessage
from .types import FixTag as FT, TYPE_MAP
from .validate import validate, convert, cast as _cast


class ListStatus(FixMessage):

    _msg_type = "N"

    _fields = OrderedDict({
        FT.ListID: True,
        FT.ListStatusType: True,
        FT.NoRpts: True,
        FT.ListOrderStatus: True,
        FT.RptSeq: True,
        FT.ListStatusText: False,
        FT.EncodedListStatusTextLen: False,
        FT.EncodedListStatusText: False,
        FT.TransactTime: False,
        FT.TotNoOrders: True,
        FT.NoOrders: True,
        FT.ClOrdID: True,
        FT.CumQty: True,
        FT.OrdStatus: True,
        FT.LeavesQty: True,
        FT.CxlQty: True,
        FT.AvgPx: True,
        FT.OrdRejReason: False,
        FT.Text: False,
        FT.EncodedTextLen: False,
        FT.EncodedText: False,
    })

    def __init__(
        self,
        list_id: str,
        list_status_type: int,
        no_rpts: int,
        list_order_status: int,
        rpt_seq: int,
        tot_no_orders: int,
        no_orders: int,
        cl_ord_id: str,
        cum_qty: Decimal,
        ord_status: str,
        leaves_qty: Decimal,
        cxl_qty: Decimal,
        avg_px: Decimal,
    ) -> None:
        super().__init__()
        self.append_pair(35, self._msg_type)
        self.append_pair(
            FT.ListID,
            convert("STRING", list_id),
        )
        self.append_pair(
            FT.ListStatusType,
            convert("INT", list_status_type),
        )
        self.append_pair(
            FT.NoRpts,
            convert("INT", no_rpts),
        )
        self.append_pair(
            FT.ListOrderStatus,
            convert("INT", list_order_status),
        )
        self.append_pair(
            FT.RptSeq,
            convert("INT", rpt_seq),
        )
        self.append_pair(
            FT.TotNoOrders,
            convert("INT", tot_no_orders),
        )
        self.append_pair(
            FT.NoOrders,
            convert("INT", no_orders),
        )
        self.append_pair(
            FT.ClOrdID,
            convert("STRING", cl_ord_id),
        )
        self.append_pair(
            FT.CumQty,
            convert("QTY", cum_qty),
        )
        self.append_pair(
            FT.OrdStatus,
            convert("CHAR", ord_status),
        )
        self.append_pair(
            FT.LeavesQty,
            convert("QTY", leaves_qty),
        )
        self.append_pair(
            FT.CxlQty,
            convert("QTY", cxl_qty),
        )
        self.append_pair(
            FT.AvgPx,
            convert("PRICE", avg_px),
        )

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ListID]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ListStatusType]) -> int:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.NoRpts]) -> int:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ListOrderStatus]) -> int:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.RptSeq]) -> int:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TotNoOrders]) -> int:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.NoOrders]) -> int:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ClOrdID]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.CumQty]) -> Decimal:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.OrdStatus]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.LeavesQty]) -> Decimal:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.CxlQty]) -> Decimal:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.AvgPx]) -> Decimal:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ListStatusText]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.EncodedListStatusTextLen]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.EncodedListStatusText]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.TransactTime]) -> t.Optional[dt.datetime]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.OrdRejReason]) -> t.Optional[int]:
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
        tag: te.Literal[FT.ListID],
        val: str,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.ListStatusType],
        val: int,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.NoRpts],
        val: int,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.ListOrderStatus],
        val: int,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.RptSeq],
        val: int,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.ListStatusText],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.EncodedListStatusTextLen],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.EncodedListStatusText],
        val: t.Optional[str],
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
        tag: te.Literal[FT.TotNoOrders],
        val: int,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.NoOrders],
        val: int,
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
        tag: te.Literal[FT.CumQty],
        val: Decimal,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.OrdStatus],
        val: str,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.LeavesQty],
        val: Decimal,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.CxlQty],
        val: Decimal,
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
        tag: te.Literal[FT.OrdRejReason],
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
        if tag is FT.ListID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.ListStatusType:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.NoRpts:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.ListOrderStatus:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.RptSeq:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.ListStatusText:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.EncodedListStatusTextLen:
            assert isinstance(val, int)
            converted = convert("LENGTH", val)
        elif tag is FT.EncodedListStatusText:
            assert isinstance(val, str)
            converted = convert("DATA", val)
        elif tag is FT.TransactTime:
            assert isinstance(val, dt.datetime)
            converted = convert("UTCTIMESTAMP", val)
        elif tag is FT.TotNoOrders:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.NoOrders:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.ClOrdID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.CumQty:
            assert isinstance(val, Decimal)
            converted = convert("QTY", val)
        elif tag is FT.OrdStatus:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.LeavesQty:
            assert isinstance(val, Decimal)
            converted = convert("QTY", val)
        elif tag is FT.CxlQty:
            assert isinstance(val, Decimal)
            converted = convert("QTY", val)
        elif tag is FT.AvgPx:
            assert isinstance(val, Decimal)
            converted = convert("PRICE", val)
        elif tag is FT.OrdRejReason:
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
    def cast(cls, msg: FixMessage) -> "ListStatus":
        return _cast(cls, msg)