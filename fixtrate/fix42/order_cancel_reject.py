import typing as t
import typing_extensions as te
from collections import OrderedDict
import datetime as dt
from decimal import Decimal

from fixtrate.message import FixMessage
from .types import FixTag as FT, TYPE_MAP
from .validate import validate, convert, cast as _cast


class OrderCancelReject(FixMessage):

    _msg_type = "9"

    _fields = OrderedDict({
        FT.OrderID: True,
        FT.SecondaryOrderID: False,
        FT.ClOrdID: True,
        FT.OrigClOrdID: True,
        FT.OrdStatus: True,
        FT.ClientID: False,
        FT.ExecBroker: False,
        FT.ListID: False,
        FT.Account: False,
        FT.TransactTime: False,
        FT.CxlRejResponseTo: True,
        FT.CxlRejReason: False,
        FT.Text: False,
        FT.EncodedTextLen: False,
        FT.EncodedText: False,
    })

    def __init__(
        self,
        order_id: str,
        cl_ord_id: str,
        orig_cl_ord_id: str,
        ord_status: str,
        cxl_rej_response_to: str,
    ) -> None:
        super().__init__()
        self.append_pair(35, self._msg_type)
        self.append_pair(
            FT.OrderID,
            convert("STRING", order_id),
        )
        self.append_pair(
            FT.ClOrdID,
            convert("STRING", cl_ord_id),
        )
        self.append_pair(
            FT.OrigClOrdID,
            convert("STRING", orig_cl_ord_id),
        )
        self.append_pair(
            FT.OrdStatus,
            convert("CHAR", ord_status),
        )
        self.append_pair(
            FT.CxlRejResponseTo,
            convert("CHAR", cxl_rej_response_to),
        )

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.OrderID]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ClOrdID]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.OrigClOrdID]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.OrdStatus]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.CxlRejResponseTo]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.SecondaryOrderID]) -> t.Optional[str]:
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
    def get(self, tag: te.Literal[FT.TransactTime]) -> t.Optional[dt.datetime]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.CxlRejReason]) -> t.Optional[int]:
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
        tag: te.Literal[FT.OrderID],
        val: str,
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
        tag: te.Literal[FT.ClOrdID],
        val: str,
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
        tag: te.Literal[FT.OrdStatus],
        val: str,
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
        tag: te.Literal[FT.TransactTime],
        val: t.Optional[dt.datetime],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.CxlRejResponseTo],
        val: str,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.CxlRejReason],
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
        if tag is FT.OrderID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.SecondaryOrderID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.ClOrdID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.OrigClOrdID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.OrdStatus:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.ClientID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.ExecBroker:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.ListID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.Account:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.TransactTime:
            assert isinstance(val, dt.datetime)
            converted = convert("UTCTIMESTAMP", val)
        elif tag is FT.CxlRejResponseTo:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        elif tag is FT.CxlRejReason:
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
    def cast(cls, msg: FixMessage) -> "OrderCancelReject":
        return _cast(cls, msg)