import pytest

from fixation import (
    constants as fc,
    dictionary as fd
)
from fixation.factories import fix44


@pytest.fixture
def fix_dict():
    return fd.FixDictionary.from_xml('/Users/carloholl/Downloads/gemini-fix-dictionary.xml')


@pytest.fixture
def market_data_request(fix_session):
    msg = fix44.market_data_request(
        symbols=['GLNG', 'NAT'],
        entry_types=[et for et in fc.MDEntryType],
    )
    fix_session.append_standard_header(msg)
    return msg


def test_correctly_validates_msg(fix_dict, market_data_request):
    fix_dict.validate_msg(market_data_request)