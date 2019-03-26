import pytest
from fixtrate import types
from iso3166 import Country as _Country
from iso4217 import Currency as _Currency
import datetime as dt


def test_integer_type():
    with pytest.raises(types.InvalidTypeError):
        types.Int.load('a')

    assert types.Int.load('1') == 1
    assert types.Int.load(1) == 1


def test_positive_integer():
    with pytest.raises(types.InvalidTypeError):
        types.PositiveInt.load('-1')
    with pytest.raises(types.InvalidTypeError):
        types.PositiveInt.load(-1)
    assert types.PositiveInt.load('1') == 1
    assert types.PositiveInt.load(1) == 1


def test_day_of_month_type():
    with pytest.raises(types.InvalidTypeError):
        types.DayOfMonth.load('0')
    with pytest.raises(types.InvalidTypeError):
        types.DayOfMonth.load('32')
    assert types.DayOfMonth.load('31') == 31


def test_currency_type():
    with pytest.raises(types.InvalidTypeError):
        types.Currency.load('YOL')
    currency = types.Currency.load('USD')
    assert currency == _Currency.usd
    assert types.Currency.dumps(currency) == 'USD'


def test_country_type():
    with pytest.raises(types.InvalidTypeError):
        types.Country.load('USA')
    with pytest.raises(types.InvalidTypeError):
        types.Country.load('YO')
    country = types.Country.load('US')
    assert isinstance(country, _Country)
    assert types.Country.dumps(country) == 'US'


def test_multiple_value_string():
    string = 'val1 val2'
    values = types.MultipleValueString.load(string)
    assert isinstance(values, tuple)
    assert len(values) == 2


def test_utc_timestamp_type():
    with pytest.raises(types.InvalidTypeError):
        types.UTCTimestamp.load('not a date')

    string = '19981231-23:59:59'
    date = types.UTCTimestamp.load(string)
    assert isinstance(date, dt.datetime)
    assert types.UTCTimestamp.dumps(date) == string


def test_date_only_type():
    with pytest.raises(types.InvalidTypeError):
        types.UTCDateOnly.load('not a date')

    string = '19981231'
    date = types.UTCDateOnly.load(string)
    assert isinstance(date, dt.datetime)
    assert types.UTCDateOnly.dumps(date) == string


def test_time_only_type():
    with pytest.raises(types.InvalidTypeError):
        types.UTCTimeOnly.load('not a date')

    string = '23:59:59'
    date = types.UTCTimeOnly.load(string)
    assert isinstance(date, dt.datetime)
    assert types.UTCTimeOnly.dumps(date) == string


def test_local_market_date_type():
    with pytest.raises(types.InvalidTypeError):
        types.LocalMarketDate.load('not a date')

    string = '19981231-23:59:59'
    date = types.LocalMarketDate.load(string)
    assert isinstance(date, dt.datetime)
    assert types.LocalMarketDate.dumps(date) == string
