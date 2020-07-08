import datetime as dt
from decimal import Decimal
import typing as t
from fixtrate.message import FixMessage
from .types import TYPE_MAP


MONTHS = {
    f"0{v}" if v > 9 else v
    for v in range(1, 12 + 1)
}


VF = t.TypeVar("VF", bound=t.Callable[[str], t.Any])
CF = t.TypeVar("CF", bound=t.Callable[[t.Any], str])
validators: t.Dict[str, t.Callable[[str], t.Any]] = {}
converters: t.Dict[str, t.Callable[[str], t.Any]] = {}


def validator(*types: str) -> t.Callable[[VF], VF]:
    def decorator(f: VF) -> VF:
        for type in types:
            validators[type] = f
        return f
    return decorator


def converter(*types: str) -> t.Callable[[CF], CF]:
    def decorator(f: CF) -> CF:
        for type in types:
            converters[type] = f
        return f
    return decorator


@validator("STRING", "CHAR", "EXCHANGE", "CURRENCY")
@converter("STRING", "CHAR", "EXCHANGE", "CURRENCY")
def validate_str(val: str) -> str:
    return val


@validator("BOOLEAN")
def validate_bool(val: str) -> bool:
    if val == "Y":
        return True
    if val == "N":
        return False
    raise ValueError


@converter("BOOLEAN")
def convert_bool(val: bool) -> str:
    if val:
        return "Y"
    else:
        return "N"


@validator("INT")
def validate_int(val: str) -> int:
    return int(val)


@converter("INT")
def convert_int(val: int) -> str:
    return str(val)


@validator("LENGTH")
def validate_length(val: str) -> int:
    as_int = int(val)
    if as_int < 0:
        raise ValueError(
            "Value of 'LENGTH' data type must be "
            "greater than zero"
        )
    return as_int


@converter("LENGTH")
def convert_length(val: int) -> str:
    if val < 0:
        raise ValueError(
            "Value of 'LENGTH' data type must be "
            "greater than zero"
        )
    return str(val)


@validator("FLOAT")
def validate_float(val: str) -> float:
    return float(val)


@converter("FLOAT")
def convert_float(val: float) -> str:
    return str(val)


@validator(
    "AMT",
    "QTY",
    "PRICE",
    "PRICEOFFSET"
)
def validate_decimal(val: str) -> Decimal:
    return Decimal(val)


@converter(
    "AMT",
    "QTY",
    "PRICE",
    "PRICEOFFSET"
)
def convert_decimal(val: Decimal) -> str:
    return str(val)


@validator("LOCALMKTDATE", "UTCDATE")
def validate_date(val: str) -> dt.date:
    format = "%Y%m%d"
    return dt.datetime.strptime(val, format).date()


@converter("LOCALMKTDATE", "UTCDATE")
def convert_date(val: dt.date) -> str:
    format = "%Y%m%d"
    return val.strftime(format)


@validator("UTCTIMEONLY")
def validate_time(val: str) -> dt.time:
    return dt.time.fromisoformat(val)


@converter("UTCTIMEONLY")
def convert_time(val: dt.time) -> str:
    return val.isoformat()


@validator("UTCTIMESTAMP")
def validate_datetime(val: str) -> dt.datetime:
    format = "%Y%m%d-%H:%M:%S"
    try:
        date = dt.datetime.strptime(val, format)
    except ValueError:
        date = dt.datetime.strptime(val, f"{format}.%f")
    return date


@converter("UTCTIMESTAMP")
def convert_datetime(val: dt.datetime) -> str:
    format = "%Y%m%d-%H:%M:%S.%f"
    return val.strftime(format)


@validator("MONTHYEAR")
@converter("MONTHYEAR")
def validate_month(val: str) -> str:
    assert val in MONTHS
    return val


@validator("DAYOFMONTH")
def validate_dom(val: str) -> int:
    asint = int(val)
    assert asint in range(1, 31 + 1)
    return asint


@converter("DAYOFMONTH")
def convert_dom(val: int) -> str:
    if val not in range(1, 31 + 1):
        raise ValueError(
            "Value of type 'DAYOFMONTH' must be "
            "a positive integer between 1 and 31"
        )
    return str(val)


@validator("MULTIPLEVALUESTRING")
def validate_multi_string(val: str) -> t.Iterable[str]:
    return val.split(" ")


@converter("MULTIPLEVALUESTRING")
def convert_multi_string(val: t.Iterable[str]) -> str:
    return " ".join(val)


def validate(type: str, val: str) -> t.Any:
    validator = validators[type]
    return validator(val)


T = t.TypeVar("T", bound=FixMessage)


def convert(type: str, val: t.Any) -> str:
    try:
        converter = converters[type]
    except KeyError as error:
        raise ValueError(
            "No converter found for data type "
            f"{type}"
        ) from error
    return converter(val)


def cast(
    cls: t.Type[T],
    base: FixMessage
) -> T:
    for field, required in cls._fields.items():
        val = base.get_raw(field)
        if val is None:
            if required:
                raise ValueError
            continue
        validate(TYPE_MAP[field], val)
    msg = cls.__new__(cls)
    msg._msg = base._msg
    return msg
