import typing as t
import typing_extensions as te
from collections import OrderedDict
import datetime as dt
from decimal import Decimal

from fix.message import FixMessage
from .types import FixTag as FT, TYPE_MAP
from .validate import validate, convert, cast as _cast


class Logon(FixMessage):

    _msg_type = "A"

    _fields = OrderedDict({
        FT.EncryptMethod: True,
        FT.HeartBtInt: True,
        FT.RawDataLength: False,
        FT.RawData: False,
        FT.ResetSeqNumFlag: False,
        FT.MaxMessageSize: False,
        FT.NoMsgTypes: False,
        FT.RefMsgType: False,
        FT.MsgDirection: False,
    })

    def __init__(
        self,
        encrypt_method: int,
        heart_bt_int: int,
    ) -> None:
        super().__init__()
        self.append_pair(35, self._msg_type)
        self.append_pair(
            FT.EncryptMethod,
            convert("INT", encrypt_method),
        )
        self.append_pair(
            FT.HeartBtInt,
            convert("INT", heart_bt_int),
        )

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.EncryptMethod]) -> int:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.HeartBtInt]) -> int:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.RawDataLength]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.RawData]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.ResetSeqNumFlag]) -> t.Optional[bool]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.MaxMessageSize]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.NoMsgTypes]) -> t.Optional[int]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.RefMsgType]) -> t.Optional[str]:
        ...

    @t.overload  # NOQA
    def get(self, tag: te.Literal[FT.MsgDirection]) -> t.Optional[str]:
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
        tag: te.Literal[FT.EncryptMethod],
        val: int,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.HeartBtInt],
        val: int,
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.RawDataLength],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.RawData],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.ResetSeqNumFlag],
        val: t.Optional[bool],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.MaxMessageSize],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.NoMsgTypes],
        val: t.Optional[int],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.RefMsgType],
        val: t.Optional[str],
    ) -> None:
        ...

    @t.overload  # NOQA
    def append(
        self,
        tag: te.Literal[FT.MsgDirection],
        val: t.Optional[str],
    ) -> None:
        ...

    def append(self, tag: FT, val: t.Any):  # NOQA
        if tag is FT.EncryptMethod:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.HeartBtInt:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.RawDataLength:
            assert isinstance(val, int)
            converted = convert("LENGTH", val)
        elif tag is FT.RawData:
            assert isinstance(val, str)
            converted = convert("DATA", val)
        elif tag is FT.ResetSeqNumFlag:
            assert isinstance(val, bool)
            converted = convert("BOOLEAN", val)
        elif tag is FT.MaxMessageSize:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.NoMsgTypes:
            assert isinstance(val, int)
            converted = convert("INT", val)
        elif tag is FT.RefMsgType:
            assert isinstance(val, str)
            converted = convert("STRING", val)
        elif tag is FT.MsgDirection:
            assert isinstance(val, str)
            converted = convert("CHAR", val)
        else:
            raise ValueError(f"{tag} is not a valid FIX tag")
        self.append_pair(tag, converted)

    @classmethod
    def cast(cls, msg: FixMessage) -> "Logon":
        return _cast(cls, msg)