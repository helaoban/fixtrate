import typing as t
import typing_extensions as te
from collections import OrderedDict
import datetime as dt
from decimal import Decimal

from fixtrate.message import FixMessage
from .types import FixTag as FT, TYPE_MAP
from .validate import validate, convert, cast as _cast


class BusinessMessageReject(FixMessage):

    _msg_type = "j"

    _fields = OrderedDict({
        FT.RefSeqNum: False,
        FT.RefMsgType: True,
        FT.BusinessRejectRefID: False,
        FT.BusinessRejectReason: True,
        FT.Text: False,
        FT.EncodedTextLen: False,
        FT.EncodedText: False,
    })

    def __init__(
        self,
        ref_msg_type: str,
        business_reject_reason: int,
    ) -> None:
        super().__init__()
        self.append_pair(35, self._msg_type)
        self.append_pair(
            FT.RefMsgType,
            convert("STRING", ref_msg_type),
        )
        self.append_pair(
            FT.BusinessRejectReason,
            convert("INT", business_reject_reason),
        )

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.RefMsgType]) -> str:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.BusinessRejectReason]) -> int:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.RefSeqNum]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.BusinessRejectRefID]) -> t.Optional[str]:
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
        tag: te.Literal[FT.RefSeqNum],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.RefMsgType],
        val: str,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.BusinessRejectRefID],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.BusinessRejectReason],
        val: int,
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
        if tag is FT.RefSeqNum:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.RefMsgType:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.BusinessRejectRefID:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.BusinessRejectReason:
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
    def cast(cls, msg: FixMessage) -> "BusinessMessageReject":
        return _cast(cls, msg)