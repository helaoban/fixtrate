import os

import pytest

from fixtrate import (
    constants as fc,
    dictionary as fd
)
from fixtrate.factories import fix42

here = os.path.dirname(__file__)


@pytest.fixture
def fix_dict():
    return fd.FixDictionary.from_xml(os.path.join(here, 'gemini-fix-dictionary.xml'))


@pytest.fixture
def market_data_request(fix_session):
    msg = fix42.market_data_request(
        symbols=['GLNG', 'NAT'],
        entry_types=[et for et in fc.MDEntryType],
    )
    fix_session._append_standard_header(msg, 1)
    return msg


def test_correctly_validates_msg(fix_dict, market_data_request):
    fix_dict.validate_msg(market_data_request)